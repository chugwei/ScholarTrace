"""Add versioned pipeline and data-collection design records.

Revision ID: 0008
Revises: 0007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _create_design_table(
    name: str,
    identifier: str,
    parent_identifier: str,
    version_constraint: str,
    content_constraint: str,
) -> None:
    op.create_table(
        name,
        sa.Column(identifier, sa.String(length=40), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(parent_identifier, sa.String(length=40), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("approved_by", sa.String(length=128), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.project_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint(identifier),
        sa.UniqueConstraint("project_id", "version", name=version_constraint),
        sa.UniqueConstraint("project_id", "content_sha256", name=content_constraint),
    )
    op.create_index(op.f(f"{name}_project_id"), name, ["project_id"], unique=False)
    op.create_index(op.f(f"{name}_{parent_identifier}"), name, [parent_identifier], unique=False)


def upgrade() -> None:
    _create_design_table(
        "pipeline_specs",
        "pipeline_id",
        "parent_pipeline_id",
        "uq_pipeline_project_version",
        "uq_pipeline_project_content",
    )
    _create_design_table(
        "data_collection_protocols",
        "protocol_id",
        "parent_protocol_id",
        "uq_protocol_project_version",
        "uq_protocol_project_content",
    )


def downgrade() -> None:
    op.drop_index(
        op.f("data_collection_protocols_parent_protocol_id"), table_name="data_collection_protocols"
    )
    op.drop_index(
        op.f("data_collection_protocols_project_id"), table_name="data_collection_protocols"
    )
    op.drop_table("data_collection_protocols")
    op.drop_index(op.f("pipeline_specs_parent_pipeline_id"), table_name="pipeline_specs")
    op.drop_index(op.f("pipeline_specs_project_id"), table_name="pipeline_specs")
    op.drop_table("pipeline_specs")
