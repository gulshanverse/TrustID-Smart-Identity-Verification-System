"""persist verification lifecycle state

Revision ID: 009_verification_lifecycle
Revises: 008_reports_metadata
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "009_verification_lifecycle"
down_revision: str | None = "008_reports_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("verifications", sa.Column("status", sa.String(24), nullable=True))
    op.execute("UPDATE verifications SET status = 'PENDING' WHERE status IS NULL")
    op.alter_column("verifications", "status", nullable=False, server_default="PENDING")


def downgrade() -> None:
    op.drop_column("verifications", "status")
