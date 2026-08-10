"""Add versioned, evidence-linked innovation candidates.

Revision ID: 0010
Revises: 0009
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "innovation_candidates",
        sa.Column("candidate_id", sa.String(length=40), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("algorithm_id", sa.String(length=40), nullable=False),
        sa.Column("prior_art_map_id", sa.String(length=40), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("parent_candidate_id", sa.String(length=40), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("approved_by", sa.String(length=128), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.project_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["algorithm_id"], ["algorithm_specs.algorithm_id"]),
        sa.ForeignKeyConstraint(["prior_art_map_id"], ["prior_art_maps.map_id"]),
        sa.PrimaryKeyConstraint("candidate_id"),
        sa.UniqueConstraint(
            "project_id",
            "algorithm_id",
            "version",
            name="uq_innovation_candidate_version",
        ),
        sa.UniqueConstraint("project_id", "content_sha256", name="uq_innovation_candidate_content"),
    )
    op.create_index(
        op.f("innovation_candidates_project_id"),
        "innovation_candidates",
        ["project_id"],
    )
    op.create_index(
        op.f("innovation_candidates_algorithm_id"),
        "innovation_candidates",
        ["algorithm_id"],
    )
    op.create_index(
        op.f("innovation_candidates_prior_art_map_id"),
        "innovation_candidates",
        ["prior_art_map_id"],
    )
    op.create_index(
        op.f("innovation_candidates_parent_candidate_id"),
        "innovation_candidates",
        ["parent_candidate_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("innovation_candidates_parent_candidate_id"),
        table_name="innovation_candidates",
    )
    op.drop_index(
        op.f("innovation_candidates_prior_art_map_id"),
        table_name="innovation_candidates",
    )
    op.drop_index(
        op.f("innovation_candidates_algorithm_id"),
        table_name="innovation_candidates",
    )
    op.drop_index(
        op.f("innovation_candidates_project_id"),
        table_name="innovation_candidates",
    )
    op.drop_table("innovation_candidates")
