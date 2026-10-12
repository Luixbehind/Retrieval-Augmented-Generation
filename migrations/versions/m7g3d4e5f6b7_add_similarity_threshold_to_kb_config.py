"""add similarity_threshold to knowledge_bases.config

The RAG chat's similarity cutoff was a hardcoded constant in retrieval_service.py; it now
lives per-knowledge-base in the same JSON config blob as top_k/hybrid weights, so each base
can be tuned independently from the "Configuração de retrieval" tab.

Revision ID: m7g3d4e5f6b7
Revises: l6f2c3d4e5a6
Create Date: 2026-08-27 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "m7g3d4e5f6b7"
down_revision: Union[str, Sequence[str], None] = "l6f2c3d4e5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "ALTER TABLE knowledge_bases ALTER COLUMN config SET DEFAULT "
        "json_build_object('top_k', 5, 'hybrid_weight_bm25', 0.7, 'hybrid_weight_vector', 0.3, "
        "'similarity_threshold', 0.1)"
    )
    op.execute(
        "UPDATE knowledge_bases "
        "SET config = (config::jsonb || jsonb_build_object('similarity_threshold', 0.1))::json "
        "WHERE NOT (config::jsonb ? 'similarity_threshold')"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "ALTER TABLE knowledge_bases ALTER COLUMN config SET DEFAULT "
        "json_build_object('top_k', 5, 'hybrid_weight_bm25', 0.7, 'hybrid_weight_vector', 0.3)"
    )
    op.execute(
        "UPDATE knowledge_bases "
        "SET config = (config::jsonb - 'similarity_threshold')::json"
    )
