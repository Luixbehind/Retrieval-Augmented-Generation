from __future__ import annotations

import html
import json
import re
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import UUID

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.legal_chunk import LegalChunk
from app.models.legal_document import LegalDocument, LegalDocumentProcessingStatusEnum
from app.prompts.lgpd_analysis import build_structured_schema_terms_prompt
from app.repositories.knowledge_bases_repository import mark_edited_if_published
from app.repositories.legal_documents_repository import (
    archive_active_reports_for_knowledge_base,
    mark_report_completed,
    mark_report_failed,
    save_compliance_report_chunks,
    start_compliance_report,
)
from app.schemas.lgpd_compliance import LgpdComplianceResponse
from app.services.document_processing import call_ollama_json, normalize_embedding, request_embedding

LGPD_FILE_PATH = Path("data/legal/lgpd/lgpd_clean.txt")
REPORT_STORAGE_DIR = Path(settings.report_storage_dir)


def _load_lgpd_context() -> str:
    resolved_path = LGPD_FILE_PATH.expanduser()
    if not resolved_path.exists():
        raise RuntimeError(f"LGPD file not found at {resolved_path}")

    lgpd_text = resolved_path.read_text(encoding="utf-8-sig").strip()
    if not lgpd_text:
        raise RuntimeError(f"LGPD file is empty at {resolved_path}")
    return lgpd_text


# O LLM às vezes emite barras invertidas soltas (caminhos, "R$\d", LaTeX-like) que não formam
# uma sequência de escape JSON válida (\", \\, \/, \b, \f, \n, \r, \t, \uXXXX) e quebram json.loads
# com "Invalid \escape". Escapamos essas barras antes de tentar novamente.
_INVALID_JSON_ESCAPE = re.compile(r'\\(?!["\\/bfnrtu])')


def _sanitize_json_escapes(text: str) -> str:
    return _INVALID_JSON_ESCAPE.sub(r"\\\\", text)


def _parse_json_object(candidate: str) -> dict | None:
    for text_to_try in (candidate, _sanitize_json_escapes(candidate)):
        try:
            parsed = json.loads(text_to_try)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _extract_json_object(raw: str) -> dict:
    cleaned = raw.strip()
    if not cleaned:
        raise ValueError("LLM returned empty response")

    parsed = _parse_json_object(cleaned)
    if parsed is not None:
        return parsed

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        parsed = _parse_json_object(cleaned[start : end + 1])
        if parsed is not None:
            return parsed

    raise ValueError("LLM response was not valid JSON")


def build_report_sections(report: LgpdComplianceResponse) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = [
        ("Resumo executivo", report.summary.strip() or "Resumo não informado."),
        (
            "Pontos corretos",
            "\n".join(report.points_correct) if report.points_correct else "Nenhum ponto correto identificado.",
        ),
        (
            "Pontos fora da lei",
            "\n".join(report.points_outside_law) if report.points_outside_law else "Nenhum ponto fora da lei identificado.",
        ),
        (
            "Artigos da LGPD aplicáveis",
            "\n".join(
                f"{item.article}: {item.description}" for item in report.applicable_articles
            )
            if report.applicable_articles
            else "Nenhum artigo aplicável identificado.",
        ),
        (
            "Riscos",
            "\n".join(report.risks) if report.risks else "Nenhum risco identificado.",
        ),
        (
            "Recomendações",
            "\n".join(report.recommendations) if report.recommendations else "Nenhuma recomendação identificada.",
        ),
    ]
    return sections


def _finalize_completed_report(
    db: Session,
    report: LgpdComplianceResponse,
    *,
    legal_document_id: UUID,
    knowledge_base_id: UUID,
) -> None:
    """Grava as seções/embeddings do relatório já gerado pelo LLM no LegalDocument PENDING
    criado antecipadamente, arquiva o relatório COMPLETED anterior (se houver) e marca este
    como COMPLETED. Se qualquer etapa falhar, nada é persistido (rollback) e o relatório
    anterior, se existia, permanece intacto e ativo."""
    try:
        archive_active_reports_for_knowledge_base(db, knowledge_base_id=knowledge_base_id)
        mark_edited_if_published(db, knowledge_base_id=knowledge_base_id)
        sections = build_report_sections(report)
        save_compliance_report_chunks(db, legal_document_id=legal_document_id, sections=sections)

        chunk_rows = db.execute(
            select(LegalChunk).where(LegalChunk.document_id == legal_document_id)
        ).scalars().all()

        for chunk_row in chunk_rows:
            chunk_text = (chunk_row.content or "").strip()
            if not chunk_text:
                continue
            chunk_row.embedding = normalize_embedding(request_embedding(chunk_text))

        result_payload = report.model_dump(mode="json")
        result_payload["report_id"] = str(legal_document_id)
        mark_report_completed(db, legal_document_id=legal_document_id, result=result_payload)
    except Exception:
        db.rollback()
        raise


def _render_section_body(section_content: str) -> str:
    if not section_content or not section_content.strip():
        return "<p>Nenhum conteúdo informado.</p>"

    lines = [line.strip() for line in section_content.splitlines()]
    bullets: list[str] = []
    paragraphs: list[str] = []

    for line in lines:
        if not line:
            continue
        if line.startswith("- ") or line.startswith("* "):
            bullets.append(f"<li>{html.escape(line[2:])}</li>")
        else:
            paragraphs.append(f"<p>{html.escape(line).replace(chr(10), '<br/>')}</p>")

    if bullets:
        paragraphs.append(f"<ul>{''.join(bullets)}</ul>")

    return "\n".join(paragraphs) if paragraphs else "<p>Nenhum conteúdo informado.</p>"


def build_readable_report_html(report_title: str, sections: list[tuple[str, str]]) -> str:
    safe_title = html.escape(report_title)
    rendered_sections = "\n".join(
        (
            f"<section><h2>{html.escape(section_title)}</h2>{_render_section_body(section_content)}</section>"
            for section_title, section_content in sections
        )
    )
    return f"""<!doctype html>
<html lang=\"pt-BR\">
  <head>
    <meta charset=\"utf-8\" />
    <title>{safe_title}</title>
    <style>
      body {{ font-family: Arial, sans-serif; color: #1f2937; margin: 32px; line-height: 1.6; }}
      h1 {{ font-size: 2rem; margin-bottom: 16px; }}
      h2 {{ font-size: 1.2rem; color: #0f172a; margin-top: 24px; }}
      section {{ border-bottom: 1px solid #e5e7eb; padding-bottom: 16px; margin-bottom: 16px; }}
      p {{ margin: 8px 0; }}
      ul {{ margin: 8px 0 8px 20px; padding-left: 20px; }}
      li {{ margin-bottom: 6px; }}
    </style>
  </head>
  <body>
    <h1>{safe_title}</h1>
    {rendered_sections}
  </body>
</html>"""


def build_readable_report_pdf(report_title: str, sections: list[tuple[str, str]]) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title=report_title, author="RAG LGPD")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SectionTitle", parent=styles["Heading2"], textColor=colors.HexColor("#0f172a"), spaceAfter=10))
    styles.add(ParagraphStyle(name="SimpleBody", parent=styles["BodyText"], fontSize=10, leading=14, spaceAfter=6))

    story = [Paragraph(report_title, styles["Title"]), Spacer(1, 20)]

    for section_title, section_content in sections:
        story.append(Paragraph(f"<b>{html.escape(section_title)}</b>", styles["SectionTitle"]))
        for line in section_content.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            story.append(Paragraph(html.escape(stripped).replace("- ", "• "), styles["SimpleBody"]))
        story.append(Spacer(1, 12))

    doc.build(story)
    return buffer.getvalue()


def persist_report_files(
    report_id: str | UUID,
    report_title: str,
    sections: list[tuple[str, str]],
) -> dict[str, Any]:
    REPORT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    report_dir = REPORT_STORAGE_DIR / str(report_id)
    report_dir.mkdir(parents=True, exist_ok=True)

    title_for_metadata = " | ".join(
        f"{section_title}: {section_content}" for section_title, section_content in sections[:3]
    )
    html_path = report_dir / "report.html"
    pdf_path = report_dir / "report.pdf"
    metadata_path = report_dir / "metadata.json"

    html_path.write_text(build_readable_report_html(report_title, sections), encoding="utf-8")
    pdf_path.write_bytes(build_readable_report_pdf(report_title, sections))

    payload = {
        "report_id": str(report_id),
        "title": title_for_metadata or report_title,
        "html_path": str(html_path),
        "pdf_path": str(pdf_path),
        "stored_at": str(report_dir),
    }
    metadata_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    return {
        "report_id": str(report_id),
        "title": payload["title"],
        "html_path": html_path,
        "pdf_path": pdf_path,
        "stored_at": report_dir,
    }


def list_report_metadata() -> list[dict[str, Any]]:
    if not REPORT_STORAGE_DIR.exists():
        return []

    metadata: list[dict[str, Any]] = []
    for report_dir in sorted(REPORT_STORAGE_DIR.iterdir(), key=lambda item: item.name):
        if not report_dir.is_dir():
            continue
        html_file = report_dir / "report.html"
        pdf_file = report_dir / "report.pdf"
        metadata_file = report_dir / "metadata.json"
        if not html_file.exists() and not pdf_file.exists():
            continue

        title_source = report_dir.name
        if metadata_file.exists():
            try:
                metadata_payload = json.loads(metadata_file.read_text(encoding="utf-8"))
                title_source = metadata_payload.get("title", title_source)
            except json.JSONDecodeError:
                title_source = report_dir.name
        elif html_file.exists():
            title_source = html_file.read_text(encoding="utf-8", errors="ignore")[:240]

        metadata.append(
            {
                "report_id": report_dir.name,
                "title": title_source or report_dir.name,
                "html_path": html_file,
                "pdf_path": pdf_file,
            }
        )
    return metadata


def get_report_sections_by_id(db: Session, report_id: str | UUID) -> tuple[str, list[tuple[str, str]]]:
    legal_document = db.get(LegalDocument, report_id)
    if legal_document is None:
        raise LookupError(f"Relatório não encontrado: {report_id}")
    if legal_document.processing_status != LegalDocumentProcessingStatusEnum.COMPLETED:
        raise LookupError(f"Relatório ainda não está pronto (status: {legal_document.processing_status.value})")

    rows = (
        db.execute(
            select(LegalChunk)
            .where(LegalChunk.document_id == legal_document.id)
            .order_by(LegalChunk.created_at.asc(), LegalChunk.id.asc())
        )
        .scalars()
        .all()
    )
    sections = [(row.article or "Relatório", row.content or "") for row in rows]
    return legal_document.title, sections


def _slugify_report_name(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return normalized[:80] or "relatorio-lgpd"


def start_lgpd_compliance_analysis(
    db: Session,
    *,
    knowledge_base_id: UUID,
    schema_file_name: str,
    terms_file_name: str,
) -> LegalDocument:
    """Cria (síncrono, rápido, sem chamar o LLM) o registro PENDING que rastreia a análise.
    Chame isso na própria requisição HTTP, depois dispare `run_lgpd_compliance_analysis`
    em background com o id retornado. O título vem dos nomes dos arquivos enviados, não de um
    campo digitado à parte."""
    schema_stem = Path(schema_file_name).stem
    terms_stem = Path(terms_file_name).stem
    title = f"Relatório de Compliance LGPD - {schema_stem} + {terms_stem}"
    return start_compliance_report(
        db,
        knowledge_base_id=knowledge_base_id,
        title=title,
        version="report-v1",
        schema_file_name=schema_file_name,
        terms_file_name=terms_file_name,
    )


def run_lgpd_compliance_analysis(
    database_url: str,
    *,
    legal_document_id: UUID,
    schema_sql: str,
    terms_text: str,
    knowledge_base_id: UUID,
) -> None:
    """Executa a chamada bloqueante ao LLM e finaliza o LegalDocument PENDING. Roda via
    BackgroundTasks com sua própria engine/sessão, já que a sessão da requisição HTTP não
    existe mais quando esta função é chamada."""
    engine = create_engine(database_url, pool_pre_ping=True)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_factory()
    try:
        lgpd_context = _load_lgpd_context()
        prompt = build_structured_schema_terms_prompt(
            lgpd_context=lgpd_context,
            schema_sql=schema_sql,
            terms_text=terms_text,
        )

        response = call_ollama_json(
            "/api/generate",
            {
                "model": settings.llm_model,
                "prompt": prompt,
                "stream": False,
            },
        )

        llm_text = str(response.get("response", "")).strip()
        payload = _extract_json_object(llm_text)
        report = LgpdComplianceResponse.model_validate(payload)
        _finalize_completed_report(
            db, report, legal_document_id=legal_document_id, knowledge_base_id=knowledge_base_id
        )
    except Exception as exc:  # noqa: BLE001 - background task must capture any processing failure
        try:
            mark_report_failed(db, legal_document_id=legal_document_id, error_message=str(exc))
        except Exception:
            db.rollback()
    finally:
        db.close()
        engine.dispose()
