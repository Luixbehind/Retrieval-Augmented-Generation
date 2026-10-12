"""Avaliação do pipeline RAG (retrieval + geração) com RAGAS, usando o Ollama local como LLM-judge."""
from __future__ import annotations

import asyncio
import math
import time
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.content_environment import ContentEnvironmentEnum
from app.repositories.evaluations_repository import (
    create_evaluation_result,
    create_evaluation_run,
    list_golden_questions,
    mark_evaluation_run_completed,
    mark_evaluation_run_failed,
    mark_evaluation_run_running,
)
from app.services.answer_generation import generate_report_answer
from app.services.document_processing import normalize_embedding, request_embedding
from app.services.retrieval_service import DEFAULT_SIMILARITY_THRESHOLD, RetrievalService

RAGAS_METRIC_NAMES = ("faithfulness", "answer_relevancy", "context_precision", "context_recall")


def start_evaluation_run(db: Session, *, knowledge_base_id: UUID) -> dict[str, object]:
    """Cria (síncrono, rápido, sem chamar o LLM) o registro PENDING que rastreia a avaliação.
    Chame isso na própria requisição HTTP, depois dispare `run_evaluation` em background com o
    id retornado."""
    return create_evaluation_run(
        db,
        knowledge_base_id=knowledge_base_id,
        judge_model=settings.ragas_judge_model or settings.llm_model,
        embedding_model=settings.embedding_model,
    )


def _retrieve_and_answer(
    db: Session, *, knowledge_base_id: UUID, question: str
) -> tuple[str | None, list[str], int]:
    started_at = time.perf_counter()
    embedding = request_embedding(question)
    normalized_embedding = normalize_embedding(embedding)
    retrieval_service = RetrievalService(db)

    results = asyncio.run(
        retrieval_service.retrieve_lgpd(
            normalized_embedding,
            question,
            similarity_threshold=DEFAULT_SIMILARITY_THRESHOLD,
            environment=ContentEnvironmentEnum.PUBLISHED,
            knowledge_base_id=knowledge_base_id,
        )
    )
    answer = generate_report_answer(question, results)
    latency_ms = int((time.perf_counter() - started_at) * 1000)
    contexts = [item["content"] for item in results if item.get("content")]
    return answer, contexts, latency_ms


def _run_ragas(rows: list[dict[str, object]]) -> list[dict[str, float | None]]:
    """Roda as métricas RAGAS sobre as linhas avaliáveis (com resposta gerada) e devolve os
    scores por linha, na mesma ordem de entrada."""
    # ragas (via `import ragas.executor`) chama nest_asyncio.apply() já no import do módulo, o
    # que falha ("Can't patch loop of type uvloop.Loop") sob o Uvicorn: a policy de event loop
    # do processo é a do uvloop, então o simples `asyncio.get_event_loop()` do nest_asyncio já
    # autocria um uvloop.Loop nesta thread. Por isso a troca de policy + loop "puro" precisa
    # envolver também os imports do ragas (não só a chamada de evaluate()), senão o patch já
    # falha na primeira vez que o módulo é importado no processo.
    original_policy = asyncio.get_event_loop_policy()
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
    try:
        pure_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(pure_loop)
        try:
            from langchain_ollama import ChatOllama, OllamaEmbeddings
            from ragas import EvaluationDataset, RunConfig, evaluate
            from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness

            # Defaults do ragas (timeout=180s, max_workers=16) foram calibrados para APIs de LLM
            # hospedadas; contra um Ollama local CPU-only cada chamada já leva ~60-90s sozinha, e
            # 16 jobs concorrentes disputando a mesma instância batem no timeout antes de terminar
            # (visto como métricas NaN silenciosas). Rodamos sequencial (max_workers=1) com um
            # timeout bem maior.
            run_config = RunConfig(timeout=1800, max_workers=1)

            judge_llm = ChatOllama(
                model=settings.ragas_judge_model or settings.llm_model, base_url=settings.ollama_base_url
            )
            judge_embeddings = OllamaEmbeddings(
                model=settings.embedding_model, base_url=settings.ollama_base_url
            )

            dataset = EvaluationDataset.from_list(
                [
                    {
                        "user_input": row["question"],
                        "response": row["answer"],
                        "retrieved_contexts": row["contexts"] or [""],
                        "reference": row["reference_answer"],
                    }
                    for row in rows
                ]
            )

            result = evaluate(
                dataset=dataset,
                metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
                llm=judge_llm,
                embeddings=judge_embeddings,
                run_config=run_config,
                show_progress=False,
            )
        finally:
            pure_loop.close()
            asyncio.set_event_loop(None)
    finally:
        asyncio.set_event_loop_policy(original_policy)

    scores_df = result.to_pandas()

    per_row_scores: list[dict[str, float | None]] = []
    for _, score_row in scores_df.iterrows():
        row_scores: dict[str, float | None] = {}
        for metric_name in RAGAS_METRIC_NAMES:
            value = score_row.get(metric_name)
            row_scores[metric_name] = None if value is None or (isinstance(value, float) and math.isnan(value)) else float(value)
        per_row_scores.append(row_scores)
    return per_row_scores


def _average(values: list[float | None]) -> float | None:
    usable = [value for value in values if value is not None]
    return sum(usable) / len(usable) if usable else None


def run_evaluation(database_url: str, *, evaluation_run_id: UUID, knowledge_base_id: UUID) -> None:
    """Executa a avaliação RAGAS completa (bloqueante) e finaliza o EvaluationRun PENDING. Roda
    via BackgroundTasks com sua própria engine/sessão, já que a sessão da requisição HTTP não
    existe mais quando esta função é chamada."""
    engine = create_engine(database_url, pool_pre_ping=True)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_factory()
    try:
        mark_evaluation_run_running(db, evaluation_run_id=evaluation_run_id)

        golden_questions = list_golden_questions(db, knowledge_base_id=knowledge_base_id)

        prepared_rows: list[dict[str, object]] = []
        for golden_question in golden_questions:
            answer, contexts, latency_ms = _retrieve_and_answer(
                db, knowledge_base_id=knowledge_base_id, question=golden_question["question"]
            )
            prepared_rows.append(
                {
                    "golden_question_id": golden_question["id"],
                    "question": golden_question["question"],
                    "reference_answer": golden_question["reference_answer"],
                    "answer": answer,
                    "contexts": contexts,
                    "latency_ms": latency_ms,
                }
            )

        evaluable_rows = [row for row in prepared_rows if row["answer"]]
        scores_by_index = {}
        if evaluable_rows:
            scores = _run_ragas(evaluable_rows)
            evaluable_ids = [row["golden_question_id"] for row in evaluable_rows]
            scores_by_index = dict(zip(evaluable_ids, scores))

        metric_totals: dict[str, list[float | None]] = {name: [] for name in RAGAS_METRIC_NAMES}
        for row in prepared_rows:
            row_scores = scores_by_index.get(row["golden_question_id"], {})
            for metric_name in RAGAS_METRIC_NAMES:
                metric_totals[metric_name].append(row_scores.get(metric_name))

            create_evaluation_result(
                db,
                evaluation_run_id=evaluation_run_id,
                golden_question_id=row["golden_question_id"],
                question=row["question"],
                generated_answer=row["answer"],
                retrieved_contexts=row["contexts"],
                latency_ms=row["latency_ms"],
                faithfulness=row_scores.get("faithfulness"),
                answer_relevancy=row_scores.get("answer_relevancy"),
                context_precision=row_scores.get("context_precision"),
                context_recall=row_scores.get("context_recall"),
            )

        mark_evaluation_run_completed(
            db,
            evaluation_run_id=evaluation_run_id,
            avg_faithfulness=_average(metric_totals["faithfulness"]),
            avg_answer_relevancy=_average(metric_totals["answer_relevancy"]),
            avg_context_precision=_average(metric_totals["context_precision"]),
            avg_context_recall=_average(metric_totals["context_recall"]),
        )
    except Exception as exc:  # noqa: BLE001 - background task must capture any processing failure
        try:
            mark_evaluation_run_failed(db, evaluation_run_id=evaluation_run_id, error_message=str(exc))
        except Exception:
            db.rollback()
    finally:
        db.close()
        engine.dispose()
