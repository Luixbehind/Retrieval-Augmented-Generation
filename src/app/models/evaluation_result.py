from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EvaluationResult(Base):
    """Resultado da avaliação RAGAS de uma golden question dentro de um evaluation run."""

    __tablename__ = "evaluation_results"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    evaluation_run_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    golden_question_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("golden_questions.id", ondelete="SET NULL"),
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    generated_answer: Mapped[str | None] = mapped_column(Text)
    retrieved_contexts: Mapped[list | None] = mapped_column(JSON)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    faithfulness: Mapped[float | None] = mapped_column(Float)
    answer_relevancy: Mapped[float | None] = mapped_column(Float)
    context_precision: Mapped[float | None] = mapped_column(Float)
    context_recall: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_evaluation_results_run_id", "evaluation_run_id"),
    )
