"""Add controlled-run lifecycle metadata and append-only events.

Revision ID: 0015
Revises: 0014
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("controlled_runs", sa.Column("log_relpath", sa.Text(), nullable=True))
    op.add_column("controlled_runs", sa.Column("staging_relpath", sa.Text(), nullable=True))
    op.add_column("controlled_runs", sa.Column("published_relpath", sa.Text(), nullable=True))
    op.create_table(
        "controlled_run_events",
        sa.Column("event_id", sa.String(length=80), nullable=False),
        sa.Column("execution_id", sa.String(length=40), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("stream", sa.String(length=16), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["execution_id"], ["controlled_runs.execution_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("event_id"),
        sa.UniqueConstraint("execution_id", "sequence", name="uq_controlled_run_event_sequence"),
    )
    op.create_index(
        op.f("controlled_run_events_execution_id"),
        "controlled_run_events",
        ["execution_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("controlled_run_events_execution_id"), table_name="controlled_run_events")
    op.drop_table("controlled_run_events")
    op.drop_column("controlled_runs", "published_relpath")
    op.drop_column("controlled_runs", "staging_relpath")
    op.drop_column("controlled_runs", "log_relpath")
