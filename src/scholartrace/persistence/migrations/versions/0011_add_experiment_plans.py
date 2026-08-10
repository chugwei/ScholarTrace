"""Add versioned, freeze-gated experiment plans.

Revision ID: 0011
Revises: 0010
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "experiment_plans",
        sa.Column("plan_id", sa.String(length=40), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("algorithm_id", sa.String(length=40), nullable=False),
        sa.Column("candidate_id", sa.String(length=40), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("parent_plan_id", sa.String(length=40), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("approved_by", sa.String(length=128), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.project_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["algorithm_id"], ["algorithm_specs.algorithm_id"]),
        sa.ForeignKeyConstraint(["candidate_id"], ["innovation_candidates.candidate_id"]),
        sa.PrimaryKeyConstraint("plan_id"),
        sa.UniqueConstraint("project_id", "version", name="uq_experiment_plan_version"),
        sa.UniqueConstraint("project_id", "content_sha256", name="uq_experiment_plan_content"),
    )
    op.create_index(op.f("experiment_plans_project_id"), "experiment_plans", ["project_id"])
    op.create_index(op.f("experiment_plans_algorithm_id"), "experiment_plans", ["algorithm_id"])
    op.create_index(op.f("experiment_plans_candidate_id"), "experiment_plans", ["candidate_id"])
    op.create_index(op.f("experiment_plans_parent_plan_id"), "experiment_plans", ["parent_plan_id"])


def downgrade() -> None:
    op.drop_index(op.f("experiment_plans_parent_plan_id"), table_name="experiment_plans")
    op.drop_index(op.f("experiment_plans_candidate_id"), table_name="experiment_plans")
    op.drop_index(op.f("experiment_plans_algorithm_id"), table_name="experiment_plans")
    op.drop_index(op.f("experiment_plans_project_id"), table_name="experiment_plans")
    op.drop_table("experiment_plans")
