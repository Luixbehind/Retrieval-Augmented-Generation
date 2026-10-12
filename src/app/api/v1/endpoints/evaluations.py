"""Avaliação do pipeline RAG de uma knowledge base: golden dataset + execuções RAGAS."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.core.tenant_db import get_tenant_database_url, get_tenant_db
from app.repositories.evaluations_repository import (
    create_golden_question,
    get_evaluation_run_by_id,
    list_evaluation_results,
    list_evaluation_runs,
    list_golden_questions,
    soft_delete_golden_question,
)
from app.repositories.knowledge_bases_repository import (
    get_knowledge_base_by_id,
    knowledge_base_exists,
    mark_golden_dataset_completed,
    mark_golden_dataset_failed,
    mark_golden_dataset_pending,
)
from app.schemas.evaluation import (
    EvaluationRunDetail,
    EvaluationRunListResponse,
    EvaluationRunRead,
    GoldenDatasetGenerateRequest,
    GoldenQuestionCreate,
    GoldenQuestionListResponse,
    GoldenQuestionRead,
)
from app.services.evaluation_service import run_evaluation, start_evaluation_run
from app.services.golden_dataset_service import (
    DEFAULT_NUM_QUESTIONS,
    NoPublishedReportError,
    generate_golden_dataset,
)

router = APIRouter(prefix="/knowledge-bases/{knowledge_base_id}", tags=["evaluations"])


def _require_knowledge_base(db: Session, knowledge_base_id: UUID) -> None:
    if not knowledge_base_exists(db, knowledge_base_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")


@router.post(
    "/golden-questions",
    response_model=GoldenQuestionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar pergunta do golden dataset",
    description="Cadastra uma pergunta de referência (com resposta esperada) usada nas avaliações RAGAS da base.",
    response_description="Pergunta do golden dataset criada.",
    responses={404: {"description": "Knowledge base not found"}},
)
def create_golden_question_endpoint(
    knowledge_base_id: UUID,
    payload: GoldenQuestionCreate,
    db: Session = Depends(get_tenant_db),
) -> GoldenQuestionRead:
    _require_knowledge_base(db, knowledge_base_id)
    created = create_golden_question(
        db,
        knowledge_base_id=knowledge_base_id,
        question=payload.question,
        reference_answer=payload.reference_answer,
    )
    return GoldenQuestionRead.model_validate(created)


@router.get(
    "/golden-questions",
    response_model=GoldenQuestionListResponse,
    summary="Listar golden dataset",
    description="Lista as perguntas de referência cadastradas para a knowledge base.",
    response_description="Perguntas do golden dataset.",
    responses={404: {"description": "Knowledge base not found"}},
)
def list_golden_questions_endpoint(
    knowledge_base_id: UUID,
    db: Session = Depends(get_tenant_db),
) -> GoldenQuestionListResponse:
    _require_knowledge_base(db, knowledge_base_id)
    questions = list_golden_questions(db, knowledge_base_id=knowledge_base_id)
    return GoldenQuestionListResponse(questions=[GoldenQuestionRead.model_validate(item) for item in questions])


@router.post(
    "/golden-questions/generate",
    response_model=GoldenQuestionListResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Gerar golden dataset automaticamente",
    description=(
        "Usa o LLM para propor perguntas e respostas de referência a partir do relatório de "
        "compliance PUBLISHED da knowledge base, já persistindo cada uma como golden question. "
        "As perguntas geradas ficam disponíveis para edição/remoção individual (endpoints "
        "existentes de golden-questions) antes de rodar a avaliação — mas, se nada for alterado, "
        "já são suficientes para disparar POST /evaluations/runs diretamente."
    ),
    response_description="Perguntas do golden dataset geradas e já persistidas.",
    responses={
        400: {"description": "Knowledge base has no published compliance report, or the LLM returned no usable questions"},
        404: {"description": "Knowledge base not found"},
    },
)
async def generate_golden_dataset_endpoint(
    knowledge_base_id: UUID,
    payload: GoldenDatasetGenerateRequest,
    db: Session = Depends(get_tenant_db),
) -> GoldenQuestionListResponse:
    knowledge_base = get_knowledge_base_by_id(db, knowledge_base_id)
    if knowledge_base is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

    if payload.num_questions is not None:
        num_questions = payload.num_questions
    else:
        num_questions = int((knowledge_base["config"] or {}).get("golden_dataset_size", DEFAULT_NUM_QUESTIONS))

    # golden_dataset_status espelha essa chamada síncrona também (não só a regeneração em
    # background do publish), para a tela de Avaliação ter uma única fonte de status
    # independente de qual dos dois gatilhos disparou a geração.
    mark_golden_dataset_pending(db, knowledge_base_id=knowledge_base_id)
    try:
        # Chamada bloqueante ao LLM (mesmo padrão do rag_chat): roda em threadpool para não travar
        # o event loop das demais requisições enquanto o Ollama gera as perguntas.
        created = await run_in_threadpool(
            generate_golden_dataset,
            db,
            knowledge_base_id=knowledge_base_id,
            num_questions=num_questions,
        )
    except NoPublishedReportError as exc:
        mark_golden_dataset_failed(db, knowledge_base_id=knowledge_base_id, error_message=str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ValueError as exc:
        mark_golden_dataset_failed(db, knowledge_base_id=knowledge_base_id, error_message=str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    mark_golden_dataset_completed(db, knowledge_base_id=knowledge_base_id)
    return GoldenQuestionListResponse(questions=[GoldenQuestionRead.model_validate(item) for item in created])


@router.delete(
    "/golden-questions/{golden_question_id}",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover pergunta do golden dataset",
    description="Remove (soft delete) uma pergunta de referência do golden dataset.",
    responses={404: {"description": "Golden question not found"}},
)
def delete_golden_question_endpoint(
    knowledge_base_id: UUID,
    golden_question_id: UUID,
    db: Session = Depends(get_tenant_db),
) -> None:
    deleted = soft_delete_golden_question(
        db, knowledge_base_id=knowledge_base_id, golden_question_id=golden_question_id
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Golden question not found")


@router.post(
    "/evaluations/runs",
    response_model=EvaluationRunRead,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Rodar avaliação RAGAS (background)",
    description=(
        "Dispara em segundo plano a avaliação do pipeline RAG (retrieval + geração) contra o conteúdo "
        "PUBLISHED da knowledge base, usando o golden dataset cadastrado. Calcula faithfulness, "
        "answer_relevancy, context_precision e context_recall via RAGAS (LLM-judge = Ollama local). "
        "Responde imediatamente com status PENDING — use GET /evaluations/runs/{run_id} para acompanhar."
    ),
    response_description="Status inicial (PENDING) da avaliação, com o run_id para acompanhamento.",
    responses={
        400: {"description": "Knowledge base has no golden questions"},
        404: {"description": "Knowledge base not found"},
    },
)
def start_evaluation_run_endpoint(
    knowledge_base_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_tenant_db),
    database_url: str = Depends(get_tenant_database_url),
) -> EvaluationRunRead:
    _require_knowledge_base(db, knowledge_base_id)
    if not list_golden_questions(db, knowledge_base_id=knowledge_base_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Knowledge base has no golden questions to evaluate",
        )

    evaluation_run = start_evaluation_run(db, knowledge_base_id=knowledge_base_id)

    background_tasks.add_task(
        run_evaluation,
        database_url,
        evaluation_run_id=evaluation_run["id"],
        knowledge_base_id=knowledge_base_id,
    )

    return EvaluationRunRead.model_validate(evaluation_run)


@router.get(
    "/evaluations/runs",
    response_model=EvaluationRunListResponse,
    summary="Listar execuções de avaliação",
    description="Lista as execuções de avaliação RAGAS da knowledge base, mais recentes primeiro.",
    responses={404: {"description": "Knowledge base not found"}},
)
def list_evaluation_runs_endpoint(
    knowledge_base_id: UUID,
    db: Session = Depends(get_tenant_db),
) -> EvaluationRunListResponse:
    _require_knowledge_base(db, knowledge_base_id)
    runs = list_evaluation_runs(db, knowledge_base_id=knowledge_base_id)
    return EvaluationRunListResponse(runs=[EvaluationRunRead.model_validate(item) for item in runs])


@router.get(
    "/evaluations/runs/{run_id}",
    response_model=EvaluationRunDetail,
    summary="Consultar execução de avaliação",
    description="Consulte periodicamente enquanto status for PENDING/RUNNING. Traz as métricas agregadas e o detalhe por pergunta.",
    responses={404: {"description": "Evaluation run not found"}},
)
def get_evaluation_run_endpoint(
    knowledge_base_id: UUID,
    run_id: UUID,
    db: Session = Depends(get_tenant_db),
) -> EvaluationRunDetail:
    run = get_evaluation_run_by_id(db, knowledge_base_id=knowledge_base_id, evaluation_run_id=run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation run not found")
    results = list_evaluation_results(db, evaluation_run_id=run_id)
    return EvaluationRunDetail.model_validate({**run, "results": results})
