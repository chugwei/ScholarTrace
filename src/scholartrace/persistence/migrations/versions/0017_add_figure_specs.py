"""Add versioned FigureSpec records.

Revision ID: 0017
Revises: 0016
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "figure_specs",
        sa.Column("figure_id", sa.String(length=40), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.project_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("figure_id"),
        sa.UniqueConstraint("project_id", "content_sha256", name="uq_figure_project_content"),
    )
    op.create_index(op.f("figure_specs_project_id"), "figure_specs", ["project_id"])
    op.create_index(op.f("figure_specs_status"), "figure_specs", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("figure_specs_status"), table_name="figure_specs")
    op.drop_index(op.f("figure_specs_project_id"), table_name="figure_specs")
    op.drop_table("figure_specs")
