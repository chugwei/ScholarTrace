"""Add verified, source-linked evidence cards.

Revision ID: 0007
Revises: 0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evidence_cards",
        sa.Column("evidence_card_id", sa.String(length=40), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("document_id", sa.String(length=40), nullable=False),
        sa.Column("chunk_id", sa.String(length=40), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("source_start_offset", sa.Integer(), nullable=False),
        sa.Column("source_end_offset", sa.Integer(), nullable=False),
        sa.Column("locator_kind", sa.String(length=16), nullable=False),
        sa.Column("locator_value", sa.Text(), nullable=False),
        sa.Column("verification_status", sa.String(length=16), nullable=False),
        sa.Column("verified_by", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.chunk_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.document_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.project_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("evidence_card_id"),
        sa.UniqueConstraint(
            "project_id",
            "chunk_id",
            "source_start_offset",
            "source_end_offset",
            name="uq_evidence_card_project_span",
        ),
    )
    op.create_index(op.f("ix_evidence_cards_project_id"), "evidence_cards", ["project_id"])
    op.create_index(op.f("ix_evidence_cards_document_id"), "evidence_cards", ["document_id"])
    op.create_index(op.f("ix_evidence_cards_chunk_id"), "evidence_cards", ["chunk_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_evidence_cards_chunk_id"), table_name="evidence_cards")
    op.drop_index(op.f("ix_evidence_cards_document_id"), table_name="evidence_cards")
    op.drop_index(op.f("ix_evidence_cards_project_id"), table_name="evidence_cards")
    op.drop_table("evidence_cards")
