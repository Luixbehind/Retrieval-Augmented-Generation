from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Index, Text, func, text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EvaluationRunStatusEnum(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class EvaluationRun(Base):
    """Uma execução da avaliação RAGAS do golden dataset contra o pipeline RAG de uma knowledge base."""

    __tablename__ = "evaluation_runs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    knowledge_base_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[EvaluationRunStatusEnum] = mapped_column(
        SQLEnum(EvaluationRunStatusEnum, name="evaluation_run_status_enum", native_enum=True),
        nullable=False,
        server_default=text("'PENDING'"),
    )
    environment: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'PUBLISHED'"))
    judge_model: Mapped[str | None] = mapped_column(Text)
    embedding_model: Mapped[str | None] = mapped_column(Text)
    avg_faithfulness: Mapped[float | None] = mapped_column(Float)
    avg_answer_relevancy: Mapped[float | None] = mapped_column(Float)
    avg_context_precision: Mapped[float | None] = mapped_column(Float)
    avg_context_recall: Mapped[float | None] = mapped_column(Float)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_evaluation_runs_kb_id", "knowledge_base_id"),
    )
