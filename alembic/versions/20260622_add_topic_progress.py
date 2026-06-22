"""add topic progress

Revision ID: 20260622topicprog
Revises: 20260622authsubj
Create Date: 2026-06-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260622topicprog"
down_revision: Union[str, Sequence[str], None] = "20260622authsubj"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------------------------------------------------------
    # 1. Add metadata columns to weak_topics
    # ---------------------------------------------------------
    op.add_column(
        "weak_topics",
        sa.Column("evidence", sa.Text(), nullable=True)
    )

    op.add_column(
        "weak_topics",
        sa.Column("recommendation", sa.Text(), nullable=True)
    )

    op.add_column(
        "weak_topics",
        sa.Column("mastery_status", sa.String(length=50), nullable=True)
    )

    op.add_column(
        "weak_topics",
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=True
        )
    )

    # ---------------------------------------------------------
    # 2. Add final analysis report to quiz_results
    # ---------------------------------------------------------
    op.add_column(
        "quiz_results",
        sa.Column("analysis_report", sa.Text(), nullable=True)
    )

    # ---------------------------------------------------------
    # 3. Create topic_progress table
    # ---------------------------------------------------------
    op.create_table(
        "topic_progress",
        sa.Column("id", sa.Integer(), nullable=False),

        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),

        sa.Column("weak_topic_id", sa.Integer(), nullable=True),
        sa.Column("quiz_result_id", sa.Integer(), nullable=True),

        sa.Column("topic", sa.String(length=200), nullable=False),

        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("correct_answers", sa.Integer(), nullable=True),
        sa.Column("total_questions", sa.Integer(), nullable=True),

        sa.Column("attempt_type", sa.String(length=50), nullable=True),

        sa.Column("analysis", sa.Text(), nullable=True),
        sa.Column("recommendation", sa.Text(), nullable=True),

        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=True
        ),

        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"]),
        sa.ForeignKeyConstraint(["weak_topic_id"], ["weak_topics.id"]),
        sa.ForeignKeyConstraint(["quiz_result_id"], ["quiz_results.id"]),

        sa.PrimaryKeyConstraint("id")
    )


def downgrade() -> None:
    op.drop_table("topic_progress")

    op.drop_column("quiz_results", "analysis_report")

    op.drop_column("weak_topics", "updated_at")
    op.drop_column("weak_topics", "mastery_status")
    op.drop_column("weak_topics", "recommendation")
    op.drop_column("weak_topics", "evidence")