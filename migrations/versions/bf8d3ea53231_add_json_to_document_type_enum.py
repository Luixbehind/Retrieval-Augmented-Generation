"""add_json_to_document_type_enum

Revision ID: bf8d3ea53231
Revises: cfb2253bd3f9
Create Date: 2026-04-21 20:57:47.616902

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bf8d3ea53231'
down_revision: Union[str, Sequence[str], None] = 'cfb2253bd3f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add JSON to document_type_enum."""
    # Adicionar JSON ao enum document_type_enum
    op.execute("ALTER TYPE document_type_enum ADD VALUE 'JSON' BEFORE 'DOCS'")


def downgrade() -> None:
    """Downgrade schema - Remove JSON from document_type_enum."""
    # PostgreSQL não permite remover valores de enum diretamente
    # Uma alternativa seria criar um novo enum, mas para simplificar,
    # deixamos uma nota de que isso requer intervenção manual se necessário
    op.execute("-- Cannot easily remove enum value in PostgreSQL.")
