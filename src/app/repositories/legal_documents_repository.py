from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content_environment import ContentEnvironmentEnum
from app.models.legal_chunk import LegalChunk
from app.models.legal_document import LegalDocument, LegalDocumentProcessingStatusEnum


def create_legal_document(
    db: Session,
    *,
    title: str,
    version: str,
    knowledge_base_id: UUID | None = None,
    environment: ContentEnvironmentEnum = ContentEnvironmentEnum.EDIT,
    processing_status: LegalDocumentProcessingStatusEnum = LegalDocumentProcessingStatusEnum.PENDING,
    schema_file_name: str | None = None,
    terms_file_name: str | None = None,
) -> LegalDocument:
    """Cria um novo documento legal."""
    legal_document = LegalDocument(
        title=title,
        version=version,
        knowledge_base_id=knowledge_base_id,
        environment=environment,
        processing_status=processing_status,
        schema_file_name=schema_file_name,
        terms_file_name=terms_file_name,
    )
    db.add(legal_document)
    db.flush()
    return legal_document


def archive_active_reports_for_knowledge_base(
    db: Session,
    *,
    knowledge_base_id: UUID,
    environment: ContentEnvironmentEnum = ContentEnvironmentEnum.EDIT,
) -> int:
    """Marca como excluído o relatório COMPLETED ativo da knowledge base informada (o que está
    sendo substituído). Chamada apenas quando um novo relatório termina com sucesso, para que uma
    nova análise que falhe nunca derrube o relatório anterior ainda válido."""
    now = datetime.now(timezone.utc)
    updated = db.execute(
        select(LegalDocument).where(
            LegalDocument.knowledge_base_id == knowledge_base_id,
            LegalDocument.environment == environment,
            LegalDocument.deleted_at.is_(None),
            LegalDocument.processing_status == LegalDocumentProcessingStatusEnum.COMPLETED,
        )
    ).scalars().all()

    if not updated:
        return 0

    for document in updated:
        document.deleted_at = now

    db.flush()
    return len(updated)


def archive_stale_attempts_for_knowledge_base(
    db: Session,
    *,
    knowledge_base_id: UUID,
    environment: ContentEnvironmentEnum = ContentEnvironmentEnum.EDIT,
) -> None:
    """Limpa tentativas PENDING/FAILED anteriores (nunca toca num relatório COMPLETED) antes de
    iniciar uma nova análise, para não acumular lixo de tentativas antigas."""
    now = datetime.now(timezone.utc)
    stale = db.execute(
        select(LegalDocument).where(
            LegalDocument.knowledge_base_id == knowledge_base_id,
            LegalDocument.environment == environment,
            LegalDocument.deleted_at.is_(None),
            LegalDocument.processing_status != LegalDocumentProcessingStatusEnum.COMPLETED,
        )
    ).scalars().all()

    for document in stale:
        document.deleted_at = now

    db.flush()


def start_compliance_report(
    db: Session,
    *,
    knowledge_base_id: UUID,
    title: str,
    version: str,
    environment: ContentEnvironmentEnum = ContentEnvironmentEnum.EDIT,
    schema_file_name: str | None = None,
    terms_file_name: str | None = None,
) -> LegalDocument:
    """Cria (e já commita) o registro PENDING que rastreia uma nova análise de conformidade,
    para que o status fique visível via polling antes mesmo do LLM ser chamado."""
    archive_stale_attempts_for_knowledge_base(db, knowledge_base_id=knowledge_base_id, environment=environment)
    legal_document = create_legal_document(
        db,
        title=title,
        version=version,
        knowledge_base_id=knowledge_base_id,
        environment=environment,
        processing_status=LegalDocumentProcessingStatusEnum.PENDING,
        schema_file_name=schema_file_name,
        terms_file_name=terms_file_name,
    )
    db.commit()
    db.refresh(legal_document)
    return legal_document


def get_latest_report_for_knowledge_base(
    db: Session,
    *,
    knowledge_base_id: UUID,
    environment: ContentEnvironmentEnum | None = None,
) -> LegalDocument | None:
    """Retorna a tentativa de relatório mais recente (PENDING/FAILED/COMPLETED) ainda ativa para a
    base, permitindo retomar o acompanhamento do status após navegação/reload.

    Sem `environment`, busca em qualquer ambiente: ao publicar, o documento EDIT vira PUBLISHED
    (não é duplicado), então filtrar por EDIT faria o relatório "sumir" da tela assim que a base
    fosse publicada, mesmo sem nenhuma análise nova pendente."""
    conditions = [
        LegalDocument.knowledge_base_id == knowledge_base_id,
        LegalDocument.deleted_at.is_(None),
    ]
    if environment is not None:
        conditions.append(LegalDocument.environment == environment)
    return db.execute(
        select(LegalDocument)
        .where(*conditions)
        .order_by(LegalDocument.created_at.desc())
        .limit(1)
    ).scalar()


def mark_report_completed(db: Session, *, legal_document_id: UUID, result: dict) -> None:
    document = db.get(LegalDocument, legal_document_id)
    if document is None:
        return
    document.processing_status = LegalDocumentProcessingStatusEnum.COMPLETED
    document.result_json = result
    document.error_message = None
    db.commit()


def mark_report_failed(db: Session, *, legal_document_id: UUID, error_message: str) -> None:
    document = db.get(LegalDocument, legal_document_id)
    if document is None:
        return
    document.processing_status = LegalDocumentProcessingStatusEnum.FAILED
    document.error_message = error_message[:2000]
    db.commit()


def save_compliance_report_chunks(
    db: Session,
    *,
    legal_document_id: UUID,
    sections: list[tuple[str, str]],
) -> None:
    """Salva chunks do relatório de compliance como seções."""
    for section_title, section_content in sections:
        chunk = LegalChunk(
            document_id=legal_document_id,
            article=section_title,
            section=None,
            content=section_content,
            embedding=None,
        )
        db.add(chunk)
    db.flush()
