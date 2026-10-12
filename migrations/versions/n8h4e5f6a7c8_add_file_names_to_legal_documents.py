"""add schema_file_name/terms_file_name to legal_documents

Lets the UI show which schema and terms file were used in the last compliance analysis,
without relying on parsing the free-text report title.

Revision ID: n8h4e5f6a7c8
Revises: m7g3d4e5f6b7
Create Date: 2026-08-27 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "n8h4e5f6a7c8"
down_revision: Union[str, Sequence[str], None] = "m7g3d4e5f6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("legal_documents", sa.Column("schema_file_name", sa.Text(), nullable=True))
    op.add_column("legal_documents", sa.Column("terms_file_name", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("legal_documents", "terms_file_name")
    op.drop_column("legal_documents", "schema_file_name")
