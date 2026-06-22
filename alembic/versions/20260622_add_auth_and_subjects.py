"""add auth and subjects

Revision ID: 20260622authsubj
Revises: 1027cc92fa28
Create Date: 2026-06-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260622authsubj"
down_revision: Union[str, Sequence[str], None] = "1027cc92fa28"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------------------------------------------------------
    # 1. Add authentication/personal fields to students
    # ---------------------------------------------------------
    op.add_column(
        "students",
        sa.Column("full_name", sa.String(length=150), nullable=True)
    )

    op.add_column(
        "students",
        sa.Column("email", sa.String(length=150), nullable=True)
    )

    op.add_column(
        "students",
        sa.Column("username", sa.String(length=100), nullable=True)
    )

    op.add_column(
        "students",
        sa.Column("password_hash", sa.String(length=255), nullable=True)
    )

    op.create_index(
        "ix_students_email",
        "students",
        ["email"],
        unique=True
    )

    op.create_index(
        "ix_students_username",
        "students",
        ["username"],
        unique=True
    )

    # ---------------------------------------------------------
    # 2. Create subjects table
    # ---------------------------------------------------------
    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "student_id",
            "name",
            name="uq_subject_student_name"
        ),
    )

    # ---------------------------------------------------------
    # 3. Add subject_id/title to sessions
    # ---------------------------------------------------------
    op.add_column(
        "sessions",
        sa.Column("subject_id", sa.Integer(), nullable=True)
    )

    op.add_column(
        "sessions",
        sa.Column("title", sa.String(length=200), nullable=True)
    )

    op.create_foreign_key(
        "fk_sessions_subject_id_subjects",
        "sessions",
        "subjects",
        ["subject_id"],
        ["id"]
    )

    # ---------------------------------------------------------
    # 4. Add subject_id to documents
    # ---------------------------------------------------------
    op.add_column(
        "documents",
        sa.Column("subject_id", sa.Integer(), nullable=True)
    )

    op.create_foreign_key(
        "fk_documents_subject_id_subjects",
        "documents",
        "subjects",
        ["subject_id"],
        ["id"]
    )

    # ---------------------------------------------------------
    # 5. Add subject_id to weak_topics
    # ---------------------------------------------------------
    op.add_column(
        "weak_topics",
        sa.Column("subject_id", sa.Integer(), nullable=True)
    )

    op.create_foreign_key(
        "fk_weak_topics_subject_id_subjects",
        "weak_topics",
        "subjects",
        ["subject_id"],
        ["id"]
    )

    op.create_unique_constraint(
        "uq_weak_topic_student_subject_topic",
        "weak_topics",
        ["student_id", "subject_id", "topic"]
    )

    # ---------------------------------------------------------
    # 6. Add subject_id to quiz_results
    # ---------------------------------------------------------
    op.add_column(
        "quiz_results",
        sa.Column("subject_id", sa.Integer(), nullable=True)
    )

    op.create_foreign_key(
        "fk_quiz_results_subject_id_subjects",
        "quiz_results",
        "subjects",
        ["subject_id"],
        ["id"]
    )


def downgrade() -> None:
    # ---------------------------------------------------------
    # Reverse quiz_results changes
    # ---------------------------------------------------------
    op.drop_constraint(
        "fk_quiz_results_subject_id_subjects",
        "quiz_results",
        type_="foreignkey"
    )
    op.drop_column("quiz_results", "subject_id")

    # ---------------------------------------------------------
    # Reverse weak_topics changes
    # ---------------------------------------------------------
    op.drop_constraint(
        "uq_weak_topic_student_subject_topic",
        "weak_topics",
        type_="unique"
    )

    op.drop_constraint(
        "fk_weak_topics_subject_id_subjects",
        "weak_topics",
        type_="foreignkey"
    )
    op.drop_column("weak_topics", "subject_id")

    # ---------------------------------------------------------
    # Reverse documents changes
    # ---------------------------------------------------------
    op.drop_constraint(
        "fk_documents_subject_id_subjects",
        "documents",
        type_="foreignkey"
    )
    op.drop_column("documents", "subject_id")

    # ---------------------------------------------------------
    # Reverse sessions changes
    # ---------------------------------------------------------
    op.drop_constraint(
        "fk_sessions_subject_id_subjects",
        "sessions",
        type_="foreignkey"
    )
    op.drop_column("sessions", "title")
    op.drop_column("sessions", "subject_id")

    # ---------------------------------------------------------
    # Drop subjects table
    # ---------------------------------------------------------
    op.drop_table("subjects")

    # ---------------------------------------------------------
    # Reverse students auth fields
    # ---------------------------------------------------------
    op.drop_index("ix_students_username", table_name="students")
    op.drop_index("ix_students_email", table_name="students")

    op.drop_column("students", "password_hash")
    op.drop_column("students", "username")
    op.drop_column("students", "email")
    op.drop_column("students", "full_name")