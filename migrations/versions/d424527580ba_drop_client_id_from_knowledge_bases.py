"""drop client_id from knowledge_bases

Revision ID: d424527580ba
Revises: a7c9b8d6e5f4
Create Date: 2026-08-26 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d424527580ba"
down_revision: Union[str, Sequence[str], None] = "a7c9b8d6e5f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index("idx_knowledge_bases_client_type", table_name="knowledge_bases")
    op.drop_index("idx_knowledge_bases_client_id", table_name="knowledge_bases")
    op.drop_column("knowledge_bases", "client_id")
    op.create_index("idx_knowledge_bases_type", "knowledge_bases", ["type"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_knowledge_bases_type", table_name="knowledge_bases")
    op.add_column("knowledge_bases", sa.Column("client_id", sa.Text(), nullable=True))
    op.create_index("idx_knowledge_bases_client_id", "knowledge_bases", ["client_id"], unique=False)
    op.create_index("idx_knowledge_bases_client_type", "knowledge_bases", ["client_id", "type"], unique=False)
