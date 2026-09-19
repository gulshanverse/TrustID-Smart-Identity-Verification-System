"""add durable auth sessions and idempotency constraints

Revision ID: 014_auth_idempotency
Revises: 013_decision_context_snapshot
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "014_auth_idempotency"
down_revision: str | None = "013_decision_context_snapshot"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "auth_sessions",
        sa.Column("token", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("token"),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"], unique=False)
    op.create_index("uq_case_decisions_case_id", "case_decisions", ["case_id"], unique=True)
    op.create_index(
        "uq_decision_intelligence_audit",
        "audit_events",
        ["verification_id", "actor_id"],
        unique=True,
        postgresql_where=sa.text("event_type = 'DECISION_INTELLIGENCE_COMPLETED'"),
        sqlite_where=sa.text("event_type = 'DECISION_INTELLIGENCE_COMPLETED'"),
    )


def downgrade() -> None:
    op.drop_index("uq_decision_intelligence_audit", table_name="audit_events")
    op.drop_index("uq_case_decisions_case_id", table_name="case_decisions")
    op.drop_index("ix_auth_sessions_user_id", table_name="auth_sessions")
    op.drop_table("auth_sessions")
