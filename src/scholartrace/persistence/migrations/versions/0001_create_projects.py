"""Create projects and research questions.

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("thread_id", sa.String(length=128), nullable=False),
        sa.Column("active_stage", sa.String(length=64), nullable=False),
        sa.Column("current_goal", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("project_id"),
        sa.UniqueConstraint("thread_id"),
    )
    op.create_table(
        "research_questions",
        sa.Column("research_question_id", sa.String(length=35), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.project_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("research_question_id"),
        sa.UniqueConstraint(
            "project_id",
            "content_sha256",
            name="uq_research_question_project_content",
        ),
        sa.UniqueConstraint(
            "project_id",
            "version",
            name="uq_research_question_project_version",
        ),
    )
    op.create_index(
        op.f("ix_research_questions_project_id"),
        "research_questions",
        ["project_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_research_questions_project_id"), table_name="research_questions")
    op.drop_table("research_questions")
    op.drop_table("projects")
