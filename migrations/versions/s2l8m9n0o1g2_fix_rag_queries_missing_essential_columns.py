"""fix rag_queries missing essential columns

rag_queries predates the knowledge-base/publish model: it had no knowledge_base_id at all (so a
logged query couldn't be traced back to which base answered it), only ever recorded the EDIT
side's answer/score even though every /rag-chat call also generates a PUBLISHED answer when one
exists, and `client_id` was dead weight — it was never populated by the endpoint, and is redundant
anyway since each client already has its own isolated database. This adds knowledge_base_id,
splits response/score into edited_*/published_* pairs, and drops the never-written client_id and
the now-redundant `answer` boolean (derivable from edited_response IS NOT NULL).

Revision ID: s2l8m9n0o1g2
Revises: r1k7l8m9n0f1
Create Date: 2026-08-28 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "s2l8m9n0o1g2"
down_revision: Union[str, Sequence[str], None] = "r1k7l8m9n0f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index("idx_rag_queries_client_id", table_name="rag_queries")
    op.drop_column("rag_queries", "client_id")
    op.drop_column("rag_queries", "answer")

    op.alter_column("rag_queries", "response", new_column_name="edited_response")
    op.alter_column("rag_queries", "score", new_column_name="edited_score")

    op.add_column("rag_queries", sa.Column("published_response", sa.Text(), nullable=True))
    op.add_column("rag_queries", sa.Column("published_score", sa.Float(), nullable=True))
    op.add_column(
        "rag_queries",
        sa.Column(
            "knowledge_base_id",
            sa.UUID(),
            sa.ForeignKey("knowledge_bases.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("idx_rag_queries_knowledge_base_id", "rag_queries", ["knowledge_base_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_rag_queries_knowledge_base_id", table_name="rag_queries")
    op.drop_column("rag_queries", "knowledge_base_id")
    op.drop_column("rag_queries", "published_score")
    op.drop_column("rag_queries", "published_response")

    op.alter_column("rag_queries", "edited_score", new_column_name="score")
    op.alter_column("rag_queries", "edited_response", new_column_name="response")

    op.add_column("rag_queries", sa.Column("answer", sa.Boolean(), nullable=True))
    op.add_column("rag_queries", sa.Column("client_id", sa.Text(), nullable=True))
    op.create_index("idx_rag_queries_client_id", "rag_queries", ["client_id"])
