"""Add evidence-bound DebugCase records.

Revision ID: 0016
Revises: 0015
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "debug_cases",
        sa.Column("case_id", sa.String(length=40), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("execution_id", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("category", sa.String(length=24), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.project_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["execution_id"], ["controlled_runs.execution_id"]),
        sa.PrimaryKeyConstraint("case_id"),
        sa.UniqueConstraint("project_id", "execution_id", name="uq_debug_case_project_execution"),
    )
    op.create_index(op.f("debug_cases_project_id"), "debug_cases", ["project_id"])
    op.create_index(op.f("debug_cases_execution_id"), "debug_cases", ["execution_id"])
    op.create_index(op.f("debug_cases_status"), "debug_cases", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("debug_cases_status"), table_name="debug_cases")
    op.drop_index(op.f("debug_cases_execution_id"), table_name="debug_cases")
    op.drop_index(op.f("debug_cases_project_id"), table_name="debug_cases")
    op.drop_table("debug_cases")
