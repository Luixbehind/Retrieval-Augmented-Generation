from __future__ import annotations

import json
from pathlib import Path
from typing import Literal
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.tenant_db import get_tenant_database_url, get_tenant_db
from app.models.legal_document import LegalDocument, LegalDocumentProcessingStatusEnum
from app.repositories.knowledge_bases_repository import is_knowledge_base_archived, knowledge_base_exists
from app.repositories.legal_documents_repository import get_latest_report_for_knowledge_base
from app.schemas.lgpd_compliance import LgpdComplianceResponse, LgpdComplianceStatusResponse
from app.services.document_processing import extract_document_text
from app.services.lgpd_compliance_service import (
    build_readable_report_html,
    build_readable_report_pdf,
    get_report_sections_by_id,
    run_lgpd_compliance_analysis,
    start_lgpd_compliance_analysis,
    _slugify_report_name,
)

router = APIRouter(prefix="/lgpd-compliance", tags=["lgpd-compliance"])

SCHEMA_ALLOWED_EXTENSIONS = {".sql", ".json"}
TERMS_ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024


async def _read_validated_upload(upload: UploadFile, allowed_extensions: set[str], *, field_label: str) -> bytes:
    file_name = upload.filename or field_label
    extension = Path(file_name).suffix.lower()
    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file type for {field_label} ({file_name}). "
                f"Allowed: {', '.join(sorted(allowed_extensions))}"
            ),
        )

    file_bytes = await upload.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"File {file_name} is empty")
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File {file_name} exceeds the size limit of {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB",
        )
    return file_bytes


def _format_table_schema(data: object) -> str | None:
    """Se o JSON for um dump estruturado de tabelas/colunas, formata como texto legível."""
    tables = data if isinstance(data, list) else data.get("tables") if isinstance(data, dict) else None
    if not isinstance(tables, list) or not tables:
        return None

    lines: list[str] = []
    for table in tables:
        if not isinstance(table, dict):
            return None
        name = table.get("table") or table.get("name")
        columns = table.get("columns")
        if not name or not isinstance(columns, list):
            return None

        column_descriptions: list[str] = []
        for column in columns:
            if isinstance(column, dict):
                column_name = column.get("name") or column.get("column")
                column_type = column.get("type") or column.get("data_type") or ""
                if not column_name:
                    return None
                column_descriptions.append(f"{column_name} ({column_type})" if column_type else str(column_name))
            elif isinstance(column, str):
                column_descriptions.append(column)
            else:
                return None

        lines.append(f"Tabela {name}: " + ", ".join(column_descriptions))

    return "\n".join(lines)


def _extract_schema_text(file_bytes: bytes, file_name: str, content_type: str | None) -> str:
    if Path(file_name).suffix.lower() == ".json":
        try:
            data = json.loads(file_bytes.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            data = None
        if data is not None:
            formatted = _format_table_schema(data)
            if formatted:
                return formatted

    return extract_document_text(file_bytes, file_name, content_type)


def _legal_document_to_status_response(document: LegalDocument) -> LgpdComplianceStatusResponse:
    result = None
    if document.processing_status == LegalDocumentProcessingStatusEnum.COMPLETED and document.result_json:
        result = LgpdComplianceResponse.model_validate(document.result_json)
    return LgpdComplianceStatusResponse(
        report_id=str(document.id),
        processing_status=document.processing_status.value,
        error_message=document.error_message,
        result=result,
        schema_file_name=document.schema_file_name,
        terms_file_name=document.terms_file_name,
    )


@router.post(
    "/analyze",
    response_model=LgpdComplianceStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Iniciar análise de conformidade LGPD (background)",
    description=(
        "Recebe o schema do banco de dados (.sql ou .json) e o termo de compromisso/tratamento de dados "
        "(.pdf ou .docx), extrai o texto de cada arquivo e dispara em segundo plano a comparação com a LGPD. "
        "Responde imediatamente com status PENDING e um report_id — use GET /report/{report_id}/status ou "
        "GET /knowledge-bases/{knowledge_base_id}/latest-report para acompanhar o progresso e obter o "
        "resultado estruturado quando o processing_status virar COMPLETED. O relatório fica vinculado à "
        "knowledge base informada (entra em EDIT, sujeito ao ciclo de publish dessa base)."
    ),
    response_description="Status inicial (PENDING) da análise, com o report_id para acompanhamento.",
    responses={
        400: {"description": "Invalid, empty, or unreadable file"},
        404: {"description": "Knowledge base not found"},
        409: {"description": "Knowledge base is archived"},
        413: {"description": "File exceeds the size limit"},
    },
)
async def analyze_lgpd_compliance(
    background_tasks: BackgroundTasks,
    knowledge_base_id: UUID = Form(...),
    schema_file: UploadFile = File(..., description="Schema do banco de dados (.sql ou .json)"),
    terms_file: UploadFile = File(..., description="Termo de compromisso / tratamento de dados (.pdf ou .docx)"),
    db: Session = Depends(get_tenant_db),
    database_url: str = Depends(get_tenant_database_url),
) -> LgpdComplianceStatusResponse:
    if not knowledge_base_exists(db, knowledge_base_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")
    if is_knowledge_base_archived(db, knowledge_base_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Knowledge base is archived")

    schema_bytes = await _read_validated_upload(schema_file, SCHEMA_ALLOWED_EXTENSIONS, field_label="schema_file")
    terms_bytes = await _read_validated_upload(terms_file, TERMS_ALLOWED_EXTENSIONS, field_label="terms_file")

    try:
        schema_sql = _extract_schema_text(schema_bytes, schema_file.filename or "schema", schema_file.content_type)
        terms_text = extract_document_text(terms_bytes, terms_file.filename or "termo", terms_file.content_type)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {exc}",
        ) from exc

    if len(schema_sql.strip()) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not extract enough text from the schema file",
        )
    if len(terms_text.strip()) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not extract enough text from the terms file",
        )

    legal_document = start_lgpd_compliance_analysis(
        db,
        knowledge_base_id=knowledge_base_id,
        schema_file_name=schema_file.filename or "schema",
        terms_file_name=terms_file.filename or "termo",
    )

    background_tasks.add_task(
        run_lgpd_compliance_analysis,
        database_url,
        legal_document_id=legal_document.id,
        schema_sql=schema_sql,
        terms_text=terms_text,
        knowledge_base_id=knowledge_base_id,
    )

    return _legal_document_to_status_response(legal_document)


@router.get(
    "/report/{report_id}/status",
    response_model=LgpdComplianceStatusResponse,
    summary="Consultar status de uma análise de conformidade",
    description="Consulte periodicamente enquanto processing_status for PENDING. Sobrevive à navegação/reload.",
    responses={404: {"description": "Report not found"}},
)
async def get_compliance_report_status(
    report_id: UUID,
    db: Session = Depends(get_tenant_db),
) -> LgpdComplianceStatusResponse:
    document = db.get(LegalDocument, report_id)
    if document is None or document.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return _legal_document_to_status_response(document)


@router.get(
    "/knowledge-bases/{knowledge_base_id}/latest-report",
    response_model=LgpdComplianceStatusResponse,
    summary="Consultar a última análise de conformidade de uma base",
    description=(
        "Retorna a tentativa mais recente (PENDING/FAILED/COMPLETED) ainda ativa para a base. Use ao entrar "
        "na tela da base para retomar o acompanhamento de uma análise em andamento ou recém-concluída, mesmo "
        "após navegar para outra tela ou recarregar a página."
    ),
    responses={404: {"description": "No report found for this knowledge base"}},
)
async def get_latest_compliance_report(
    knowledge_base_id: UUID,
    db: Session = Depends(get_tenant_db),
) -> LgpdComplianceStatusResponse:
    if not knowledge_base_exists(db, knowledge_base_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

    document = get_latest_report_for_knowledge_base(db, knowledge_base_id=knowledge_base_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No report found for this knowledge base"
        )
    return _legal_document_to_status_response(document)


@router.get(
    "/report/{report_id}/download",
    summary="Baixar relatório de conformidade",
    description="Faz o download do relatório persistido em HTML ou PDF, do banco do cliente identificado pelo header X-Client-Slug. Quando a API key estiver configurada, o cabeçalho X-API-Key é obrigatório.",
    response_description="Arquivo HTML ou PDF do relatório.",
    responses={
        200: {
            "description": "Relatório gerado com sucesso",
            "content": {
                "application/pdf": {"schema": {"type": "string", "format": "binary"}},
                "text/html": {"schema": {"type": "string"}},
            },
        },
        401: {"description": "Invalid or missing API key."},
        404: {"description": "Report or client not found"},
        409: {"description": "Report is not ready yet"},
    },
)
async def download_report(
    request: Request,
    report_id: UUID,
    format: Literal["html", "pdf"] = Query(
        default="pdf",
        description="Formato do arquivo de exportação.",
        examples=["pdf", "html"],
    ),
    db: Session = Depends(get_tenant_db),
) -> Response:
    if settings.report_download_api_key:
        provided_key = request.headers.get("X-API-Key")
        if provided_key != settings.report_download_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key.",
            )

    document = db.get(LegalDocument, report_id)
    if document is None or document.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    if document.processing_status != LegalDocumentProcessingStatusEnum.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Report is not ready yet (status: {document.processing_status.value})",
        )

    try:
        title, sections = get_report_sections_by_id(db, report_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - surfaced as API error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load report: {exc}",
        ) from exc

    if format == "html":
        payload = build_readable_report_html(title, sections).encode("utf-8")
        media_type = "text/html; charset=utf-8"
        extension = "html"
    else:
        payload = build_readable_report_pdf(title, sections)
        media_type = "application/pdf"
        extension = "pdf"

    file_name = f"{_slugify_report_name(title)}.{extension}"
    return StreamingResponse(
        iter([payload]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )
