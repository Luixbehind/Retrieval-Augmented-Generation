"""rename documents table to knowlegde_embeddings

Revision ID: b7d3c2a91e44
Revises: 1ccbf05ec1df
Create Date: 2026-04-21 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b7d3c2a91e44'
down_revision: Union[str, Sequence[str], None] = '1ccbf05ec1df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.rename_table('documents', 'knowlegde_embeddings')


def downgrade() -> None:
    """Downgrade schema."""
    op.rename_table('knowlegde_embeddings', 'documents')
