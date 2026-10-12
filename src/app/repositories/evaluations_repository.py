from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

GOLDEN_QUESTION_COLUMNS = "id, knowledge_base_id, question, reference_answer, created_at, updated_at, deleted_at"
EVALUATION_RUN_COLUMNS = (
    "id, knowledge_base_id, status, environment, judge_model, embedding_model, "
    "avg_faithfulness, avg_answer_relevancy, avg_context_precision, avg_context_recall, "
    "error_message, started_at, finished_at, created_at"
)
EVALUATION_RESULT_COLUMNS = (
    "id, evaluation_run_id, golden_question_id, question, generated_answer, retrieved_contexts, "
    "latency_ms, faithfulness, answer_relevancy, context_precision, context_recall, created_at"
)


def create_golden_question(
    db: Session,
    *,
    knowledge_base_id: UUID,
    question: str,
    reference_answer: str,
) -> dict[str, object]:
    try:
        created = db.execute(
            text(
                f"""
                INSERT INTO golden_questions (knowledge_base_id, question, reference_answer)
                VALUES (:knowledge_base_id, :question, :reference_answer)
                RETURNING {GOLDEN_QUESTION_COLUMNS}
                """
            ),
            {
                "knowledge_base_id": knowledge_base_id,
                "question": question,
                "reference_answer": reference_answer,
            },
        ).mappings().one()

        db.commit()
        return dict(created)
    except Exception:
        db.rollback()
        raise


def list_golden_questions(db: Session, *, knowledge_base_id: UUID) -> list[dict[str, object]]:
    rows = db.execute(
        text(
            f"""
            SELECT {GOLDEN_QUESTION_COLUMNS}
            FROM golden_questions
            WHERE knowledge_base_id = :knowledge_base_id AND deleted_at IS NULL
            ORDER BY created_at DESC, id DESC
            """
        ),
        {"knowledge_base_id": knowledge_base_id},
    ).mappings().all()
    return [dict(row) for row in rows]


def soft_delete_golden_question(db: Session, *, knowledge_base_id: UUID, golden_question_id: UUID) -> bool:
    try:
        deleted = db.execute(
            text(
                """
                UPDATE golden_questions
                SET deleted_at = :deleted_at
                WHERE id = :golden_question_id
                  AND knowledge_base_id = :knowledge_base_id
                  AND deleted_at IS NULL
                RETURNING id
                """
            ),
            {
                "golden_question_id": golden_question_id,
                "knowledge_base_id": knowledge_base_id,
                "deleted_at": datetime.now(timezone.utc),
            },
        ).first()

        if deleted is None:
            db.rollback()
            return False

        db.commit()
        return True
    except Exception:
        db.rollback()
        raise


def soft_delete_golden_questions_by_ids(db: Session, *, golden_question_ids: list[UUID]) -> int:
    """Apaga (soft delete) um conjunto específico de golden questions pelo id — usado ao regenerar
    o golden dataset após um publish, para remover só o dataset anterior (não as perguntas recém
    -criadas, que têm a mesma knowledge_base_id)."""
    if not golden_question_ids:
        return 0
    try:
        deleted = db.execute(
            text(
                """
                UPDATE golden_questions
                SET deleted_at = :deleted_at
                WHERE id = ANY(:golden_question_ids)
                  AND deleted_at IS NULL
                RETURNING id
                """
            ),
            {
                "golden_question_ids": golden_question_ids,
                "deleted_at": datetime.now(timezone.utc),
            },
        ).fetchall()

        db.commit()
        return len(deleted)
    except Exception:
        db.rollback()
        raise


def create_evaluation_run(
    db: Session,
    *,
    knowledge_base_id: UUID,
    judge_model: str,
    embedding_model: str,
) -> dict[str, object]:
    try:
        created = db.execute(
            text(
                f"""
                INSERT INTO evaluation_runs (knowledge_base_id, judge_model, embedding_model)
                VALUES (:knowledge_base_id, :judge_model, :embedding_model)
                RETURNING {EVALUATION_RUN_COLUMNS}
                """
            ),
            {
                "knowledge_base_id": knowledge_base_id,
                "judge_model": judge_model,
                "embedding_model": embedding_model,
            },
        ).mappings().one()

        db.commit()
        return dict(created)
    except Exception:
        db.rollback()
        raise


def mark_evaluation_run_running(db: Session, *, evaluation_run_id: UUID) -> None:
    db.execute(
        text(
            """
            UPDATE evaluation_runs
            SET status = 'RUNNING', started_at = :started_at
            WHERE id = :evaluation_run_id
            """
        ),
        {"evaluation_run_id": evaluation_run_id, "started_at": datetime.now(timezone.utc)},
    )
    db.commit()


def mark_evaluation_run_completed(
    db: Session,
    *,
    evaluation_run_id: UUID,
    avg_faithfulness: float | None,
    avg_answer_relevancy: float | None,
    avg_context_precision: float | None,
    avg_context_recall: float | None,
) -> None:
    db.execute(
        text(
            """
            UPDATE evaluation_runs
            SET status = 'COMPLETED',
                finished_at = :finished_at,
                avg_faithfulness = :avg_faithfulness,
                avg_answer_relevancy = :avg_answer_relevancy,
                avg_context_precision = :avg_context_precision,
                avg_context_recall = :avg_context_recall
            WHERE id = :evaluation_run_id
            """
        ),
        {
            "evaluation_run_id": evaluation_run_id,
            "finished_at": datetime.now(timezone.utc),
            "avg_faithfulness": avg_faithfulness,
            "avg_answer_relevancy": avg_answer_relevancy,
            "avg_context_precision": avg_context_precision,
            "avg_context_recall": avg_context_recall,
        },
    )
    db.commit()


def mark_evaluation_run_failed(db: Session, *, evaluation_run_id: UUID, error_message: str) -> None:
    db.execute(
        text(
            """
            UPDATE evaluation_runs
            SET status = 'FAILED', finished_at = :finished_at, error_message = :error_message
            WHERE id = :evaluation_run_id
            """
        ),
        {
            "evaluation_run_id": evaluation_run_id,
            "finished_at": datetime.now(timezone.utc),
            "error_message": error_message,
        },
    )
    db.commit()


def get_evaluation_run_by_id(
    db: Session, *, knowledge_base_id: UUID, evaluation_run_id: UUID
) -> dict[str, object] | None:
    row = db.execute(
        text(
            f"""
            SELECT {EVALUATION_RUN_COLUMNS}
            FROM evaluation_runs
            WHERE id = :evaluation_run_id AND knowledge_base_id = :knowledge_base_id
            """
        ),
        {"evaluation_run_id": evaluation_run_id, "knowledge_base_id": knowledge_base_id},
    ).mappings().first()
    return None if row is None else dict(row)


def list_evaluation_runs(db: Session, *, knowledge_base_id: UUID) -> list[dict[str, object]]:
    rows = db.execute(
        text(
            f"""
            SELECT {EVALUATION_RUN_COLUMNS}
            FROM evaluation_runs
            WHERE knowledge_base_id = :knowledge_base_id
            ORDER BY created_at DESC, id DESC
            """
        ),
        {"knowledge_base_id": knowledge_base_id},
    ).mappings().all()
    return [dict(row) for row in rows]


def list_evaluation_results(db: Session, *, evaluation_run_id: UUID) -> list[dict[str, object]]:
    rows = db.execute(
        text(
            f"""
            SELECT {EVALUATION_RESULT_COLUMNS}
            FROM evaluation_results
            WHERE evaluation_run_id = :evaluation_run_id
            ORDER BY created_at ASC, id ASC
            """
        ),
        {"evaluation_run_id": evaluation_run_id},
    ).mappings().all()
    return [dict(row) for row in rows]


def create_evaluation_result(
    db: Session,
    *,
    evaluation_run_id: UUID,
    golden_question_id: UUID | None,
    question: str,
    generated_answer: str | None,
    retrieved_contexts: list[str],
    latency_ms: int,
    faithfulness: float | None,
    answer_relevancy: float | None,
    context_precision: float | None,
    context_recall: float | None,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO evaluation_results (
                evaluation_run_id, golden_question_id, question, generated_answer, retrieved_contexts,
                latency_ms, faithfulness, answer_relevancy, context_precision, context_recall
            )
            VALUES (
                :evaluation_run_id, :golden_question_id, :question, :generated_answer,
                CAST(:retrieved_contexts AS json),
                :latency_ms, :faithfulness, :answer_relevancy, :context_precision, :context_recall
            )
            """
        ),
        {
            "evaluation_run_id": evaluation_run_id,
            "golden_question_id": golden_question_id,
            "question": question,
            "generated_answer": generated_answer,
            "retrieved_contexts": json.dumps(retrieved_contexts),
            "latency_ms": latency_ms,
            "faithfulness": faithfulness,
            "answer_relevancy": answer_relevancy,
            "context_precision": context_precision,
            "context_recall": context_recall,
        },
    )
    db.commit()
