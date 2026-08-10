"""Add versioned manuscripts, section contracts, and claim ledger.

Revision ID: 0018
Revises: 0017
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "manuscripts",
        sa.Column("manuscript_id", sa.String(length=40), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("parent_manuscript_id", sa.String(length=40), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.project_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("manuscript_id"),
        sa.UniqueConstraint("project_id", "version", name="uq_manuscript_project_version"),
        sa.UniqueConstraint("project_id", "content_sha256", name="uq_manuscript_project_content"),
    )
    op.create_index(op.f("manuscripts_project_id"), "manuscripts", ["project_id"])
    op.create_index(op.f("manuscripts_status"), "manuscripts", ["status"])
    op.create_index(
        op.f("manuscripts_parent_manuscript_id"), "manuscripts", ["parent_manuscript_id"]
    )

    op.create_table(
        "section_contracts",
        sa.Column("section_id", sa.String(length=40), nullable=False),
        sa.Column("manuscript_id", sa.String(length=40), nullable=False),
        sa.Column("section", sa.String(length=32), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["manuscript_id"], ["manuscripts.manuscript_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("section_id"),
        sa.UniqueConstraint(
            "manuscript_id",
            "section",
            name="uq_section_contract_manuscript_section",
        ),
    )
    op.create_index(op.f("section_contracts_manuscript_id"), "section_contracts", ["manuscript_id"])
    op.create_index(op.f("section_contracts_status"), "section_contracts", ["status"])

    op.create_table(
        "claim_ledger",
        sa.Column("claim_id", sa.String(length=40), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("claim_type", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.project_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("claim_id"),
        sa.UniqueConstraint("project_id", "content_sha256", name="uq_claim_project_content"),
    )
    op.create_index(op.f("claim_ledger_project_id"), "claim_ledger", ["project_id"])
    op.create_index(op.f("claim_ledger_claim_type"), "claim_ledger", ["claim_type"])
    op.create_index(op.f("claim_ledger_status"), "claim_ledger", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("claim_ledger_status"), table_name="claim_ledger")
    op.drop_index(op.f("claim_ledger_claim_type"), table_name="claim_ledger")
    op.drop_index(op.f("claim_ledger_project_id"), table_name="claim_ledger")
    op.drop_table("claim_ledger")
    op.drop_index(op.f("section_contracts_status"), table_name="section_contracts")
    op.drop_index(op.f("section_contracts_manuscript_id"), table_name="section_contracts")
    op.drop_table("section_contracts")
    op.drop_index(op.f("manuscripts_parent_manuscript_id"), table_name="manuscripts")
    op.drop_index(op.f("manuscripts_status"), table_name="manuscripts")
    op.drop_index(op.f("manuscripts_project_id"), table_name="manuscripts")
    op.drop_table("manuscripts")
