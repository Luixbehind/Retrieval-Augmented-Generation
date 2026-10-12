"""add content environment (edit/published) and EDITED knowledge base status

Revision ID: j489gh1i8d5j
Revises: i378fg0h7c4i
Create Date: 2026-08-27 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "j489gh1i8d5j"
down_revision: Union[str, Sequence[str], None] = "i378fg0h7c4i"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

content_environment_enum = postgresql.ENUM("EDIT", "PUBLISHED", name="content_environment_enum")


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    content_environment_enum.create(bind, checkfirst=True)

    op.execute("ALTER TYPE knowledge_base_status_enum ADD VALUE IF NOT EXISTS 'EDITED'")

    # knowledge_documents: new content lives in EDIT; existing rows predate this
    # feature and are already-live content, so they backfill as PUBLISHED.
    op.add_column(
        "knowledge_documents",
        sa.Column("environment", content_environment_enum, nullable=False, server_default=sa.text("'EDIT'")),
    )
    op.execute("UPDATE knowledge_documents SET environment = 'PUBLISHED'")

    # legal_documents: same backfill reasoning. Standalone reports (knowledge_base_id
    # IS NULL, from POST /lgpd-compliance/analyze) are always immediately visible,
    # so they also backfill as PUBLISHED.
    op.add_column(
        "legal_documents",
        sa.Column("environment", content_environment_enum, nullable=False, server_default=sa.text("'EDIT'")),
    )
    op.execute("UPDATE legal_documents SET environment = 'PUBLISHED'")

    op.drop_index("uq_legal_documents_active_kb_report", table_name="legal_documents")
    op.create_index(
        "uq_legal_documents_active_kb_report",
        "legal_documents",
        ["knowledge_base_id", "environment"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND knowledge_base_id IS NOT NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    raise NotImplementedError(
        "Downgrade not supported: EDITED status and EDIT/PUBLISHED content split are not reconstructible."
    )
