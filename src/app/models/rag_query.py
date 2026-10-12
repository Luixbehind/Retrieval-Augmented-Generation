from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RagQuery(Base):
    """Log de auditoria de cada chamada ao /rag-chat: pergunta, resposta e score do lado EDIT e,
    quando existir, do lado PUBLISHED da mesma knowledge base — os dois sempre são respondidos na
    mesma requisição, então os dois precisam ficar registrados no mesmo log."""

    __tablename__ = "rag_queries"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    knowledge_base_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="SET NULL"),
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    edited_response: Mapped[str | None] = mapped_column(Text)
    edited_score: Mapped[float | None] = mapped_column(Float)
    published_response: Mapped[str | None] = mapped_column(Text)
    published_score: Mapped[float | None] = mapped_column(Float)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    model_name: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[object | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[object | None] = mapped_column(DateTime)

    __table_args__ = (
        Index("idx_rag_queries_knowledge_base_id", "knowledge_base_id"),
    )
