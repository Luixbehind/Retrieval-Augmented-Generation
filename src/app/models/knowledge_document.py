from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlalchemy import DateTime, Index, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DocumentTypeEnum(str, Enum):
    PDF = "PDF"
    TXT = "TXT"
    DOCS = "DOCS"


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    client_id: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    document_type: Mapped[DocumentTypeEnum | None] = mapped_column(
        SQLEnum(DocumentTypeEnum, name="document_type_enum", native_enum=True)
    )
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[object | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[object | None] = mapped_column(DateTime)

    __table_args__ = (
        Index("idx_knowledge_documents_client_id", "client_id"),
        Index("idx_knowledge_documents_client_created_at", "client_id", created_at.desc()),
    )
