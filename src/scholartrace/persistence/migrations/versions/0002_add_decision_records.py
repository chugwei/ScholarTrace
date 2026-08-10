"""Add auditable human decision records.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "decision_records",
        sa.Column("decision_id", sa.String(length=128), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("thread_id", sa.String(length=128), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.project_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("decision_id"),
        sa.UniqueConstraint("project_id", "decision_id", name="uq_decision_project_id"),
    )
    op.create_index(
        op.f("ix_decision_records_project_id"),
        "decision_records",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_decision_records_thread_id"),
        "decision_records",
        ["thread_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_decision_records_thread_id"), table_name="decision_records")
    op.drop_index(op.f("ix_decision_records_project_id"), table_name="decision_records")
    op.drop_table("decision_records")
