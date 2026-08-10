"""Add versioned algorithm specifications and prior-art maps.

Revision ID: 0009
Revises: 0008
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _create_versioned_table(
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
        sa.Column("status", sa.String(length=24), nullable=False),
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
    _create_versioned_table(
        "algorithm_specs",
        "algorithm_id",
        "parent_algorithm_id",
        "uq_algorithm_project_version",
        "uq_algorithm_project_content",
    )
    op.create_table(
        "prior_art_maps",
        sa.Column("map_id", sa.String(length=40), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("algorithm_id", sa.String(length=40), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("parent_map_id", sa.String(length=40), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("approved_by", sa.String(length=128), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.project_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["algorithm_id"], ["algorithm_specs.algorithm_id"]),
        sa.PrimaryKeyConstraint("map_id"),
        sa.UniqueConstraint(
            "project_id", "algorithm_id", "version", name="uq_prior_art_map_version"
        ),
        sa.UniqueConstraint("project_id", "content_sha256", name="uq_prior_art_map_content"),
    )
    op.create_index(op.f("prior_art_maps_project_id"), "prior_art_maps", ["project_id"])
    op.create_index(op.f("prior_art_maps_algorithm_id"), "prior_art_maps", ["algorithm_id"])
    op.create_index(op.f("prior_art_maps_parent_map_id"), "prior_art_maps", ["parent_map_id"])


def downgrade() -> None:
    op.drop_index(op.f("prior_art_maps_parent_map_id"), table_name="prior_art_maps")
    op.drop_index(op.f("prior_art_maps_algorithm_id"), table_name="prior_art_maps")
    op.drop_index(op.f("prior_art_maps_project_id"), table_name="prior_art_maps")
    op.drop_table("prior_art_maps")
    op.drop_index(op.f("algorithm_specs_parent_algorithm_id"), table_name="algorithm_specs")
    op.drop_index(op.f("algorithm_specs_project_id"), table_name="algorithm_specs")
    op.drop_table("algorithm_specs")
