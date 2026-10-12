"""move status into knowledge_bases and drop knowledge_base_versions

Revision ID: i378fg0h7c4i
Revises: h267ef9g6b3h
Create Date: 2026-08-26 00:00:00.000002

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "i378fg0h7c4i"
down_revision: Union[str, Sequence[str], None] = "h267ef9g6b3h"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

knowledge_base_status_enum = postgresql.ENUM(
    "DRAFT", "PUBLISHED", "ARCHIVED", name="knowledge_base_status_enum"
)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    knowledge_base_status_enum.create(bind, checkfirst=True)

    op.add_column(
        "knowledge_bases",
        sa.Column(
            "status",
            knowledge_base_status_enum,
            nullable=False,
            server_default=sa.text("'DRAFT'"),
        ),
    )
    op.execute(
        """
        UPDATE knowledge_bases kb
        SET status = kbv.status::text::knowledge_base_status_enum
        FROM (
            SELECT DISTINCT ON (knowledge_base_id) knowledge_base_id, status
            FROM knowledge_base_versions
            ORDER BY knowledge_base_id, version_number DESC
        ) kbv
        WHERE kbv.knowledge_base_id = kb.id
        """
    )

    # knowledge_documents: knowledge_base_version_id -> knowledge_base_id
    op.add_column("knowledge_documents", sa.Column("knowledge_base_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute(
        """
        UPDATE knowledge_documents kd
        SET knowledge_base_id = kbv.knowledge_base_id
        FROM knowledge_base_versions kbv
        WHERE kbv.id = kd.knowledge_base_version_id
        """
    )
    op.drop_index("idx_knowledge_documents_kb_version_id", table_name="knowledge_documents")
    op.drop_index("idx_knowledge_documents_kb_version_created_at", table_name="knowledge_documents")
    op.drop_constraint(
        "fk_knowledge_documents_kb_version_id", "knowledge_documents", type_="foreignkey"
    )
    op.drop_column("knowledge_documents", "knowledge_base_version_id")
    op.create_foreign_key(
        "knowledge_documents_knowledge_base_id_fkey",
        "knowledge_documents",
        "knowledge_bases",
        ["knowledge_base_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_knowledge_documents_kb_id", "knowledge_documents", ["knowledge_base_id"])
    op.create_index(
        "idx_knowledge_documents_kb_created_at",
        "knowledge_documents",
        ["knowledge_base_id", sa.text("created_at DESC")],
    )

    # legal_documents: knowledge_base_version_id -> knowledge_base_id
    op.add_column("legal_documents", sa.Column("knowledge_base_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute(
        """
        UPDATE legal_documents ld
        SET knowledge_base_id = kbv.knowledge_base_id
        FROM knowledge_base_versions kbv
        WHERE kbv.id = ld.knowledge_base_version_id
        """
    )
    op.drop_index("idx_legal_documents_kb_version_id", table_name="legal_documents")
    op.drop_index("uq_legal_documents_active_version_report", table_name="legal_documents")
    op.drop_constraint(
        "fk_legal_documents_knowledge_base_version_id", "legal_documents", type_="foreignkey"
    )
    op.drop_column("legal_documents", "knowledge_base_version_id")
    op.create_foreign_key(
        "legal_documents_knowledge_base_id_fkey",
        "legal_documents",
        "knowledge_bases",
        ["knowledge_base_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_legal_documents_kb_id", "legal_documents", ["knowledge_base_id"])
    op.create_index(
        "uq_legal_documents_active_kb_report",
        "legal_documents",
        ["knowledge_base_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND knowledge_base_id IS NOT NULL"),
    )

    # Drop RAG comparison tables and knowledge_base_versions
    op.drop_table("rag_query_answers")
    op.drop_table("rag_query_runs")
    op.drop_table("knowledge_base_versions")

    op.execute("DROP TYPE IF EXISTS knowledge_base_version_status_enum")
    op.execute("DROP TYPE IF EXISTS query_environment_enum")


def downgrade() -> None:
    """Downgrade schema."""
    raise NotImplementedError(
        "Downgrade not supported: knowledge_base_versions and RAG comparison data are not reconstructible."
    )
