"""persist normalized external verification results

Revision ID: 012_external_verification_results
Revises: 011_phase5_rule_metadata
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "012_external_verification_results"
down_revision: str | None = "011_phase5_rule_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "external_verifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("verification_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=128), nullable=False),
        sa.Column("provider_version", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("query_reference", sa.String(length=160), nullable=True),
        sa.Column("response_timestamp", sa.String(length=64), nullable=False),
        sa.Column("demo", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["verification_id"], ["verifications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_external_verifications_verification_id", "external_verifications", ["verification_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_external_verifications_verification_id", table_name="external_verifications")
    op.drop_table("external_verifications")
