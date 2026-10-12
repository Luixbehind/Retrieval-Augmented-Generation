"""add golden_dataset_status to knowledge_bases

Golden dataset (re)generation now runs in the background (after publish, or via the manual
generate endpoint), so the frontend needs a persisted status to poll — otherwise there is no
way to know when it's safe to click "Rodar avaliação" besides blindly refetching the golden
questions list. Mirrors the PENDING/COMPLETED/FAILED pattern already used by
legal_documents.processing_status and evaluation_runs.status.

Revision ID: r1k7l8m9n0f1
Revises: q0j6k7l8m9e0
Create Date: 2026-08-28 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "r1k7l8m9n0f1"
down_revision: Union[str, Sequence[str], None] = "q0j6k7l8m9e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

golden_dataset_status_enum = sa.Enum(
    "IDLE", "PENDING", "COMPLETED", "FAILED", name="golden_dataset_status_enum"
)


def upgrade() -> None:
    """Upgrade schema."""
    golden_dataset_status_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "knowledge_bases",
        sa.Column(
            "golden_dataset_status",
            golden_dataset_status_enum,
            server_default=sa.text("'IDLE'"),
            nullable=False,
        ),
    )
    op.add_column("knowledge_bases", sa.Column("golden_dataset_error_message", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("knowledge_bases", "golden_dataset_error_message")
    op.drop_column("knowledge_bases", "golden_dataset_status")
    golden_dataset_status_enum.drop(op.get_bind(), checkfirst=True)
