"""Geração automática do golden dataset (pergunta + resposta de referência) usado na avaliação
RAGAS, a partir do relatório de compliance LGPD já publicado da knowledge base."""
from __future__ import annotations

import json
import logging
import re
from uuid import UUID

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.content_environment import ContentEnvironmentEnum
from app.models.legal_chunk import LegalChunk
from app.models.legal_document import LegalDocumentProcessingStatusEnum
from app.prompts.lgpd_analysis import build_golden_dataset_prompt
from app.repositories.evaluations_repository import (
    create_golden_question,
    list_golden_questions,
    soft_delete_golden_questions_by_ids,
)
from app.repositories.knowledge_bases_repository import (
    get_knowledge_base_by_id,
    mark_golden_dataset_completed,
    mark_golden_dataset_failed,
)
from app.repositories.legal_documents_repository import get_latest_report_for_knowledge_base
from app.services.document_processing import call_ollama_json

logger = logging.getLogger(__name__)

DEFAULT_NUM_QUESTIONS = 8

# Mesmo problema de escapes inválidos do LLM descrito em lgpd_compliance_service._sanitize_json_escapes.
_INVALID_JSON_ESCAPE = re.compile(r'\\(?!["\\/bfnrtu])')


class NoPublishedReportError(Exception):
    """Não há relatório de compliance PUBLISHED (ou ele ainda não está COMPLETED) para a base."""


def _load_published_report_context(db: Session, *, knowledge_base_id: UUID) -> str:
    report = get_latest_report_for_knowledge_base(
        db, knowledge_base_id=knowledge_base_id, environment=ContentEnvironmentEnum.PUBLISHED
    )
    if report is None or report.processing_status != LegalDocumentProcessingStatusEnum.COMPLETED:
        raise NoPublishedReportError(
            "Knowledge base has no published compliance report to generate a golden dataset from"
        )

    chunk_rows = (
        db.execute(
            select(LegalChunk)
            .where(LegalChunk.document_id == report.id)
            .order_by(LegalChunk.created_at.asc(), LegalChunk.id.asc())
        )
        .scalars()
        .all()
    )
    context = "\n\n".join(f"[{row.article or 'Trecho'}] {row.content}" for row in chunk_rows if row.content)
    if not context.strip():
        raise NoPublishedReportError("Published compliance report has no content to generate a golden dataset from")
    return context


def _parse_json_array(candidate: str) -> list | None:
    for text_to_try in (candidate, _INVALID_JSON_ESCAPE.sub(r"\\\\", candidate)):
        try:
            parsed = json.loads(text_to_try)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, list):
            return parsed
    return None


def _extract_json_array(raw: str) -> list:
    cleaned = raw.strip()
    if not cleaned:
        raise ValueError("LLM returned empty response")

    parsed = _parse_json_array(cleaned)
    if parsed is not None:
        return parsed

    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start != -1 and end != -1 and end > start:
        parsed = _parse_json_array(cleaned[start : end + 1])
        if parsed is not None:
            return parsed

    raise ValueError("LLM response was not a valid JSON array")


def generate_golden_dataset(
    db: Session, *, knowledge_base_id: UUID, num_questions: int = DEFAULT_NUM_QUESTIONS
) -> list[dict[str, object]]:
    """Chama o LLM (bloqueante) para propor `num_questions` pares pergunta/resposta com base no
    relatório PUBLISHED da base e já persiste cada um como golden question. O usuário pode editar
    ou excluir itens individualmente depois (endpoints existentes) antes de rodar a avaliação; se
    não mexer em nada, os itens gerados aqui já são suficientes para `POST .../evaluations/runs`."""
    report_context = _load_published_report_context(db, knowledge_base_id=knowledge_base_id)
    prompt = build_golden_dataset_prompt(report_context=report_context, num_questions=num_questions)

    response = call_ollama_json(
        "/api/generate",
        {
            "model": settings.llm_model,
            "prompt": prompt,
            "stream": False,
        },
    )
    llm_text = str(response.get("response", "")).strip()
    proposed_items = _extract_json_array(llm_text)

    created: list[dict[str, object]] = []
    for item in proposed_items[:num_questions]:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question") or "").strip()
        reference_answer = str(item.get("reference_answer") or "").strip()
        if not question or not reference_answer:
            continue
        created.append(
            create_golden_question(
                db,
                knowledge_base_id=knowledge_base_id,
                question=question,
                reference_answer=reference_answer,
            )
        )

    if not created:
        raise ValueError("LLM did not return any usable question/reference_answer pairs")

    return created


def regenerate_golden_dataset_on_publish(database_url: str, *, knowledge_base_id: UUID) -> None:
    """Chamada via BackgroundTasks logo após um publish bem-sucedido. Um publish só acontece quando
    há conteúdo EDIT pendente (senão a API responde 409), então todo publish bem-sucedido implica um
    relatório PUBLISHED novo — o golden dataset anterior referenciava a versão anterior do relatório
    e não é mais o gabarito correto para avaliar a versão atual. Por isso apagamos (soft delete) TODAS
    as golden questions existentes (geradas ou cadastradas manualmente) e geramos um dataset novo a
    partir do relatório recém-publicado, para a aba Avaliação já vir com o que precisa para rodar.
    O usuário ainda pode revisar/editar/excluir itens antes de rodar a avaliação — só não sobrevivem
    a um novo publish, porque nesse momento deixam de refletir o relatório atual.
    Roda com sua própria engine/sessão, como as outras tarefas de background — e nunca propaga erro,
    já que é um efeito colateral do publish, não o publish em si."""
    engine = create_engine(database_url, pool_pre_ping=True)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_factory()
    try:
        knowledge_base = get_knowledge_base_by_id(db, knowledge_base_id)
        if knowledge_base is None:
            return

        # Guardamos os ids do dataset ANTIGO antes de gerar o novo, para apagar exatamente esses
        # (nunca por knowledge_base_id direto: isso também pegaria as perguntas recém-criadas, que
        # têm a mesma knowledge_base_id).
        stale_ids = [question["id"] for question in list_golden_questions(db, knowledge_base_id=knowledge_base_id)]

        num_questions = int((knowledge_base["config"] or {}).get("golden_dataset_size", DEFAULT_NUM_QUESTIONS))
        created = generate_golden_dataset(db, knowledge_base_id=knowledge_base_id, num_questions=num_questions)

        # Só apaga o dataset antigo depois que o novo já foi gerado com sucesso: se o LLM falhar
        # (NoPublishedReportError, resposta inválida etc.), o dataset anterior continua intacto e
        # utilizável em vez de a base ficar sem nenhuma golden question.
        removed = soft_delete_golden_questions_by_ids(db, golden_question_ids=stale_ids)
        mark_golden_dataset_completed(db, knowledge_base_id=knowledge_base_id)
        logger.info(
            "Regenerated golden dataset for knowledge_base_id=%s after publish: removed %d, created %d",
            knowledge_base_id,
            removed,
            len(created),
        )
    except NoPublishedReportError as exc:
        logger.info(
            "Skipped golden dataset regeneration for knowledge_base_id=%s: no published compliance report yet",
            knowledge_base_id,
        )
        mark_golden_dataset_failed(db, knowledge_base_id=knowledge_base_id, error_message=str(exc))
    except Exception as exc:  # noqa: BLE001 - background task must never break the publish flow
        logger.exception(
            "Golden dataset regeneration failed for knowledge_base_id=%s", knowledge_base_id
        )
        try:
            mark_golden_dataset_failed(db, knowledge_base_id=knowledge_base_id, error_message=str(exc))
        except Exception:
            db.rollback()
    finally:
        db.close()
        engine.dispose()
