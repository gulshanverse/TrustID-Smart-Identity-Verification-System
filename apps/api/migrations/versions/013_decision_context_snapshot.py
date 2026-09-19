"""persist immutable Phase 6 context with officer decisions

Revision ID: 013_decision_context_snapshot
Revises: 012_external_verify_results
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "013_decision_context_snapshot"
down_revision: str | None = "012_external_verify_results"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("case_decisions", sa.Column("decision_context", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("case_decisions", "decision_context")
