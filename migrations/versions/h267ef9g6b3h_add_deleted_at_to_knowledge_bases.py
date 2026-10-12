"""add deleted_at to knowledge_bases

Revision ID: h267ef9g6b3h
Revises: d424527580ba
Create Date: 2026-08-26 00:00:00.000001

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "h267ef9g6b3h"
down_revision: Union[str, Sequence[str], None] = "d424527580ba"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("knowledge_bases", sa.Column("deleted_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("knowledge_bases", "deleted_at")
