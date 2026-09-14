"""add report metadata

Revision ID: 008_reports_metadata
Revises: 007_cases_workflow
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "008_reports_metadata"
down_revision: str | None = "007_cases_workflow"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table("reports", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("report_type", sa.String(32), nullable=False), sa.Column("reference_type", sa.String(32), nullable=False), sa.Column("reference_id", sa.Uuid(), nullable=False), sa.Column("generated_by", sa.Uuid(), nullable=False), sa.Column("report_version", sa.String(32), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["generated_by"], ["users.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_reports_reference_id", "reports", ["reference_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_reports_reference_id", table_name="reports")
    op.drop_table("reports")
