"""add golden_questions, evaluation_runs and evaluation_results tables

Suporte à avaliação do pipeline RAG via RAGAS: golden_questions guarda o dataset de
referência (pergunta + resposta esperada) por knowledge base; evaluation_runs rastreia
cada execução da avaliação (status, modelos usados, médias das métricas); e
evaluation_results guarda o resultado por pergunta dentro de um run.

Revision ID: p9i5j6k7l8d9
Revises: n8h4e5f6a7c8
Create Date: 2026-08-27 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "p9i5j6k7l8d9"
down_revision: Union[str, Sequence[str], None] = "n8h4e5f6a7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

evaluation_run_status_enum = postgresql.ENUM(
    "PENDING", "RUNNING", "COMPLETED", "FAILED", name="evaluation_run_status_enum", create_type=False
)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    evaluation_run_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "golden_questions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("knowledge_base_id", sa.UUID(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("reference_answer", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_golden_questions_kb_id", "golden_questions", ["knowledge_base_id"], unique=False)

    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("knowledge_base_id", sa.UUID(), nullable=False),
        sa.Column("status", evaluation_run_status_enum, server_default=sa.text("'PENDING'"), nullable=False),
        sa.Column("environment", sa.Text(), server_default=sa.text("'PUBLISHED'"), nullable=False),
        sa.Column("judge_model", sa.Text(), nullable=True),
        sa.Column("embedding_model", sa.Text(), nullable=True),
        sa.Column("avg_faithfulness", sa.Float(), nullable=True),
        sa.Column("avg_answer_relevancy", sa.Float(), nullable=True),
        sa.Column("avg_context_precision", sa.Float(), nullable=True),
        sa.Column("avg_context_recall", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_evaluation_runs_kb_id", "evaluation_runs", ["knowledge_base_id"], unique=False)

    op.create_table(
        "evaluation_results",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("evaluation_run_id", sa.UUID(), nullable=False),
        sa.Column("golden_question_id", sa.UUID(), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("generated_answer", sa.Text(), nullable=True),
        sa.Column("retrieved_contexts", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("faithfulness", sa.Float(), nullable=True),
        sa.Column("answer_relevancy", sa.Float(), nullable=True),
        sa.Column("context_precision", sa.Float(), nullable=True),
        sa.Column("context_recall", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["evaluation_run_id"], ["evaluation_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["golden_question_id"], ["golden_questions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_evaluation_results_run_id", "evaluation_results", ["evaluation_run_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_evaluation_results_run_id", table_name="evaluation_results")
    op.drop_table("evaluation_results")
    op.drop_index("idx_evaluation_runs_kb_id", table_name="evaluation_runs")
    op.drop_table("evaluation_runs")
    op.drop_index("idx_golden_questions_kb_id", table_name="golden_questions")
    op.drop_table("golden_questions")

    bind = op.get_bind()
    evaluation_run_status_enum.drop(bind, checkfirst=True)
