"""add knowledge_base_version reference to legal_documents

Revision ID: a7c9b8d6e5f4
Revises: g156de8f5a2g
Create Date: 2026-08-22 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a7c9b8d6e5f4"
down_revision: Union[str, Sequence[str], None] = "g156de8f5a2g"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "legal_documents",
        sa.Column("knowledge_base_version_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_legal_documents_knowledge_base_version_id",
        "legal_documents",
        "knowledge_base_versions",
        ["knowledge_base_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "idx_legal_documents_kb_version_id",
        "legal_documents",
        ["knowledge_base_version_id"],
        unique=False,
    )
    op.create_index(
        "uq_legal_documents_active_version_report",
        "legal_documents",
        ["knowledge_base_version_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND knowledge_base_version_id IS NOT NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_legal_documents_active_version_report", table_name="legal_documents")
    op.drop_index("idx_legal_documents_kb_version_id", table_name="legal_documents")
    op.drop_constraint(
        "fk_legal_documents_knowledge_base_version_id",
        "legal_documents",
        type_="foreignkey",
    )
    op.drop_column("legal_documents", "knowledge_base_version_id")
