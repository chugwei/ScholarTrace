"""Add append-only claim updates bound to metric results.

Revision ID: 0013
Revises: 0012
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "claim_updates",
        sa.Column("update_id", sa.String(length=40), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("claim_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("metric_result_ids", sa.JSON(), nullable=False),
        sa.Column("run_ids", sa.JSON(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.project_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("update_id"),
    )
    op.create_index(op.f("claim_updates_project_id"), "claim_updates", ["project_id"])
    op.create_index(op.f("claim_updates_claim_id"), "claim_updates", ["claim_id"])
    op.create_index(op.f("claim_updates_status"), "claim_updates", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("claim_updates_status"), table_name="claim_updates")
    op.drop_index(op.f("claim_updates_claim_id"), table_name="claim_updates")
    op.drop_index(op.f("claim_updates_project_id"), table_name="claim_updates")
    op.drop_table("claim_updates")
