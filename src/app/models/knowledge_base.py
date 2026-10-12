from __future__ import annotations

from datetime import datetime
from enum import Enum

from uuid import UUID

from sqlalchemy import DateTime, Index, Text, func, text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSON, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class KnowledgeBaseStatusEnum(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    EDITED = "EDITED"
    ARCHIVED = "ARCHIVED"


class GoldenDatasetStatusEnum(str, Enum):
    IDLE = "IDLE"
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str | None] = mapped_column(Text)
    config: Mapped[dict | None] = mapped_column(
        JSON,
        server_default=func.cast(
            func.json_build_object(
                "top_k", 5, "hybrid_weight_bm25", 0.7, "hybrid_weight_vector", 0.3, "similarity_threshold", 0.1,
                "golden_dataset_size", 8,
            ),
            JSON,
        ),
        nullable=False,
    )
    status: Mapped[KnowledgeBaseStatusEnum] = mapped_column(
        SQLEnum(KnowledgeBaseStatusEnum, name="knowledge_base_status_enum", native_enum=True),
        nullable=False,
        server_default=text("'DRAFT'"),
    )
    golden_dataset_status: Mapped[GoldenDatasetStatusEnum] = mapped_column(
        SQLEnum(GoldenDatasetStatusEnum, name="golden_dataset_status_enum", native_enum=True),
        nullable=False,
        server_default=text("'IDLE'"),
    )
    golden_dataset_error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[object | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[object | None] = mapped_column(DateTime)

    __table_args__ = (
        Index("idx_knowledge_bases_type", "type"),
    )
