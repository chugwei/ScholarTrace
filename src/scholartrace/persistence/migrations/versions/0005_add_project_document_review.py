"""Add project document relevance and review metadata.

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("project_documents") as batch_op:
        batch_op.add_column(sa.Column("relevance_score", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("relevance_reason", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("decided_by", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("decided_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("project_documents") as batch_op:
        batch_op.drop_column("decided_at")
        batch_op.drop_column("decided_by")
        batch_op.drop_column("relevance_reason")
        batch_op.drop_column("relevance_score")
