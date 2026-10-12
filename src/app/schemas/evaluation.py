from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.evaluation_run import EvaluationRunStatusEnum


class GoldenQuestionCreate(BaseModel):
    question: str = Field(
        min_length=1,
        description="Pergunta de referência do golden dataset.",
        examples=["Quais são os princípios da LGPD previstos no Art. 6º?"],
    )
    reference_answer: str = Field(
        min_length=1,
        description="Resposta esperada (ground truth) usada pelas métricas context_precision/context_recall.",
        examples=[
            "O Art. 6º da LGPD prevê os princípios de finalidade, adequação, necessidade, livre acesso, "
            "qualidade dos dados, transparência, segurança, prevenção, não discriminação e responsabilização."
        ],
    )


class GoldenQuestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    knowledge_base_id: UUID
    question: str
    reference_answer: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class GoldenQuestionListResponse(BaseModel):
    questions: list[GoldenQuestionRead]


class GoldenDatasetGenerateRequest(BaseModel):
    num_questions: int | None = Field(
        default=None,
        ge=3,
        le=20,
        description=(
            "Quantidade de perguntas a gerar. Se omitido, usa o default da knowledge base "
            "(config.golden_dataset_size, 8 caso a base não tenha um valor configurado)."
        ),
    )


class EvaluationResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    golden_question_id: UUID | None = None
    question: str
    generated_answer: str | None = None
    retrieved_contexts: list[str] = Field(default_factory=list)
    latency_ms: int | None = None
    faithfulness: float | None = None
    answer_relevancy: float | None = None
    context_precision: float | None = None
    context_recall: float | None = None
    created_at: datetime | None = None


class EvaluationRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    knowledge_base_id: UUID
    status: EvaluationRunStatusEnum
    environment: str
    judge_model: str | None = None
    embedding_model: str | None = None
    avg_faithfulness: float | None = None
    avg_answer_relevancy: float | None = None
    avg_context_precision: float | None = None
    avg_context_recall: float | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime | None = None


class EvaluationRunDetail(EvaluationRunRead):
    results: list[EvaluationResultRead] = Field(default_factory=list)


class EvaluationRunListResponse(BaseModel):
    runs: list[EvaluationRunRead]
