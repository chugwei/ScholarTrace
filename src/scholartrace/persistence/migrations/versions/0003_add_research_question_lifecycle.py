"""Add draft/frozen lifecycle metadata to research-question versions.

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("research_questions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "status",
                sa.String(length=16),
                nullable=False,
                server_default=sa.text("'draft'"),
            )
        )
        batch_op.add_column(sa.Column("frozen_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("frozen_by", sa.String(length=128), nullable=True))
        batch_op.add_column(
            sa.Column("parent_research_question_id", sa.String(length=35), nullable=True)
        )
        batch_op.create_index(
            "ix_research_questions_parent_research_question_id",
            ["parent_research_question_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("research_questions") as batch_op:
        batch_op.drop_index("ix_research_questions_parent_research_question_id")
        batch_op.drop_column("parent_research_question_id")
        batch_op.drop_column("frozen_by")
        batch_op.drop_column("frozen_at")
        batch_op.drop_column("status")
