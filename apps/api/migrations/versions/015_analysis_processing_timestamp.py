"""add durable analysis processing timestamp

Revision ID: 015_analysis_processing_timestamp
Revises: 014_auth_and_idempotency_integrity
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "015_analysis_processing_timestamp"
down_revision: str | None = "014_auth_and_idempotency_integrity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "verifications",
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_verifications_processing_started_at",
        "verifications",
        ["processing_started_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_verifications_processing_started_at", table_name="verifications")
    op.drop_column("verifications", "processing_started_at")
