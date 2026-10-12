"""drop unused knowledge_documents and knowlegde_embeddings tables

The generic "upload a document" pipeline (knowledge_documents + knowlegde_embeddings,
consumed by RetrievalService.retrieve_hybrid) was never wired up to any frontend screen —
the only flow the UI actually drives is the LGPD compliance pipeline, which lives entirely
in legal_documents/legal_chunks. Dropping the orphaned tables/enums/triggers.

Revision ID: l6f2c3d4e5a6
Revises: k590hi2j9e6k
Create Date: 2026-08-27 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "l6f2c3d4e5a6"
down_revision: Union[str, Sequence[str], None] = "k590hi2j9e6k"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_table("knowlegde_embeddings")
    op.drop_table("knowledge_documents")
    op.execute("DROP TYPE IF EXISTS document_type_enum")
    op.execute("DROP TYPE IF EXISTS document_processing_status_enum")


def downgrade() -> None:
    """Downgrade schema."""
    raise NotImplementedError(
        "Downgrade not supported: dropped tables/enums are not reconstructible with their data."
    )
