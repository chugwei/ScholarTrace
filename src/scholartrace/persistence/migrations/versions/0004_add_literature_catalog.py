"""Add the independent document catalog and project links.

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("document_id", sa.String(length=40), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("ingest_status", sa.String(length=24), nullable=False),
        sa.Column("quality_status", sa.String(length=32), nullable=False),
        sa.Column("searchable", sa.Boolean(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("authors", sa.JSON(), nullable=False),
        sa.Column("abstract", sa.Text(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("doi", sa.String(length=256), nullable=True),
        sa.Column("url", sa.String(length=2048), nullable=True),
        sa.Column("storage_relpath", sa.Text(), nullable=True),
        sa.Column("text_relpath", sa.Text(), nullable=True),
        sa.Column("parser_version", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("document_id"),
        sa.UniqueConstraint("content_sha256", name="uq_document_content_sha256"),
    )
    op.create_index(op.f("ix_documents_doi"), "documents", ["doi"], unique=False)
    op.create_table(
        "project_documents",
        sa.Column("project_document_id", sa.String(length=40), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("document_id", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.document_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.project_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("project_document_id"),
        sa.UniqueConstraint(
            "project_id",
            "document_id",
            name="uq_project_document_project_document",
        ),
    )
    op.create_index(
        op.f("ix_project_documents_project_id"),
        "project_documents",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_documents_document_id"),
        "project_documents",
        ["document_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_project_documents_document_id"), table_name="project_documents")
    op.drop_index(op.f("ix_project_documents_project_id"), table_name="project_documents")
    op.drop_table("project_documents")
    op.drop_index(op.f("ix_documents_doi"), table_name="documents")
    op.drop_table("documents")
