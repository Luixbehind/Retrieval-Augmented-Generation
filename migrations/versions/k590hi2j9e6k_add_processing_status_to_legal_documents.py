"""add processing_status/error_message/result_json to legal_documents

Revision ID: k590hi2j9e6k
Revises: j489gh1i8d5j
Create Date: 2026-08-27 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "k590hi2j9e6k"
down_revision: Union[str, Sequence[str], None] = "j489gh1i8d5j"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

legal_document_processing_status_enum = postgresql.ENUM(
    "PENDING", "COMPLETED", "FAILED", name="legal_document_processing_status_enum"
)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    legal_document_processing_status_enum.create(bind, checkfirst=True)

    # Existing rows all predate background-job tracking and already have their
    # chunks/report persisted, so they backfill as COMPLETED.
    op.add_column(
        "legal_documents",
        sa.Column(
            "processing_status",
            legal_document_processing_status_enum,
            nullable=False,
            server_default=sa.text("'PENDING'"),
        ),
    )
    op.execute("UPDATE legal_documents SET processing_status = 'COMPLETED'")

    op.add_column("legal_documents", sa.Column("error_message", sa.Text(), nullable=True))
    op.add_column(
        "legal_documents",
        sa.Column("result_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )

    op.create_index(
        "idx_legal_documents_processing_status", "legal_documents", ["processing_status"], unique=False
    )

    # The "only one active report per (kb, environment)" invariant now applies only
    # to COMPLETED reports, so a new PENDING/FAILED attempt can coexist with the
    # still-valid previous COMPLETED report until the new one actually succeeds.
    op.drop_index("uq_legal_documents_active_kb_report", table_name="legal_documents")
    op.create_index(
        "uq_legal_documents_active_kb_report",
        "legal_documents",
        ["knowledge_base_id", "environment"],
        unique=True,
        postgresql_where=sa.text(
            "deleted_at IS NULL AND knowledge_base_id IS NOT NULL AND processing_status = 'COMPLETED'"
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    raise NotImplementedError(
        "Downgrade not supported: processing_status backfill and index semantics are not reconstructible."
    )
