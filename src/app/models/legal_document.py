from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Text, func, text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSON, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.content_environment import ContentEnvironmentEnum

if TYPE_CHECKING:
    from app.models.legal_chunk import LegalChunk
    from app.models.knowledge_base import KnowledgeBase


class LegalDocumentProcessingStatusEnum(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class LegalDocument(Base):
    __tablename__ = "legal_documents"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    knowledge_base_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="SET NULL"),
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str | None] = mapped_column(Text)
    environment: Mapped[ContentEnvironmentEnum] = mapped_column(
        SQLEnum(ContentEnvironmentEnum, name="content_environment_enum", native_enum=True),
        nullable=False,
        server_default=text("'EDIT'"),
    )
    processing_status: Mapped[LegalDocumentProcessingStatusEnum] = mapped_column(
        SQLEnum(
            LegalDocumentProcessingStatusEnum,
            name="legal_document_processing_status_enum",
            native_enum=True,
        ),
        nullable=False,
        server_default=text("'PENDING'"),
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    result_json: Mapped[dict | None] = mapped_column(JSON)
    schema_file_name: Mapped[str | None] = mapped_column(Text)
    terms_file_name: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[object | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[object | None] = mapped_column(DateTime)

    knowledge_base: Mapped[KnowledgeBase | None] = relationship()
    chunks: Mapped[list["LegalChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index(
            "idx_legal_documents_kb_id",
            "knowledge_base_id",
        ),
        Index("idx_legal_documents_processing_status", "processing_status"),
        Index(
            "uq_legal_documents_active_kb_report",
            "knowledge_base_id",
            "environment",
            unique=True,
            postgresql_where=text(
                "deleted_at IS NULL AND knowledge_base_id IS NOT NULL AND processing_status = 'COMPLETED'"
            ),
        ),
    )
