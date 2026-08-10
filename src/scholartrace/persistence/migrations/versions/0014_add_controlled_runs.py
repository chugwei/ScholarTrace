"""Add immutable controlled-run identities and lifecycle state.

Revision ID: 0014
Revises: 0013
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "controlled_runs",
        sa.Column("execution_id", sa.String(length=40), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("plan_id", sa.String(length=40), nullable=False),
        sa.Column("matrix_entry_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("backend", sa.String(length=16), nullable=False),
        sa.Column("command_sha256", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.project_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["experiment_plans.plan_id"]),
        sa.PrimaryKeyConstraint("execution_id"),
    )
    op.create_index(op.f("controlled_runs_project_id"), "controlled_runs", ["project_id"])
    op.create_index(op.f("controlled_runs_plan_id"), "controlled_runs", ["plan_id"])
    op.create_index(op.f("controlled_runs_status"), "controlled_runs", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("controlled_runs_status"), table_name="controlled_runs")
    op.drop_index(op.f("controlled_runs_plan_id"), table_name="controlled_runs")
    op.drop_index(op.f("controlled_runs_project_id"), table_name="controlled_runs")
    op.drop_table("controlled_runs")
