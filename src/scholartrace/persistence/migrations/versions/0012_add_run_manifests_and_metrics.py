"""Add imported run manifests and provenance-aware metric results.

Revision ID: 0012
Revises: 0011
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "run_manifests",
        sa.Column("run_id", sa.String(length=40), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("plan_id", sa.String(length=40), nullable=False),
        sa.Column("matrix_entry_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.project_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["experiment_plans.plan_id"]),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index(op.f("run_manifests_project_id"), "run_manifests", ["project_id"])
    op.create_index(op.f("run_manifests_plan_id"), "run_manifests", ["plan_id"])
    op.create_index(op.f("run_manifests_status"), "run_manifests", ["status"])

    op.create_table(
        "metric_results",
        sa.Column("metric_result_id", sa.String(length=40), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("run_id", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("split", sa.String(length=128), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("verification_status", sa.String(length=16), nullable=False),
        sa.Column("is_final", sa.Boolean(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.project_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["run_manifests.run_id"]),
        sa.PrimaryKeyConstraint("metric_result_id"),
        sa.UniqueConstraint(
            "run_id", "name", "split", "source", name="uq_metric_run_name_split_source"
        ),
    )
    op.create_index(op.f("metric_results_project_id"), "metric_results", ["project_id"])
    op.create_index(op.f("metric_results_run_id"), "metric_results", ["run_id"])
    op.create_index(op.f("metric_results_status"), "metric_results", ["verification_status"])


def downgrade() -> None:
    op.drop_index(op.f("metric_results_status"), table_name="metric_results")
    op.drop_index(op.f("metric_results_run_id"), table_name="metric_results")
    op.drop_index(op.f("metric_results_project_id"), table_name="metric_results")
    op.drop_table("metric_results")
    op.drop_index(op.f("run_manifests_status"), table_name="run_manifests")
    op.drop_index(op.f("run_manifests_plan_id"), table_name="run_manifests")
    op.drop_index(op.f("run_manifests_project_id"), table_name="run_manifests")
    op.drop_table("run_manifests")
