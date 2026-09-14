"""add cases and investigation workflow

Revision ID: 007_cases_workflow
Revises: 006_risk_assessment
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "007_cases_workflow"
down_revision: str | None = "006_risk_assessment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table("cases", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("case_number", sa.String(32), nullable=False), sa.Column("verification_id", sa.Uuid(), nullable=False), sa.Column("title", sa.String(180), nullable=False), sa.Column("description", sa.String(), nullable=False), sa.Column("status", sa.String(24), nullable=False), sa.Column("priority", sa.String(16), nullable=False), sa.Column("assigned_to", sa.Uuid(), nullable=True), sa.Column("assigned_supervisor", sa.Uuid(), nullable=True), sa.Column("created_by", sa.Uuid(), nullable=False), sa.Column("resolved_by", sa.Uuid(), nullable=True), sa.Column("resolution", sa.String(32), nullable=True), sa.Column("resolution_reason", sa.String(), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True), sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True), sa.ForeignKeyConstraint(["assigned_supervisor"], ["users.id"], ondelete="SET NULL"), sa.ForeignKeyConstraint(["assigned_to"], ["users.id"], ondelete="SET NULL"), sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["resolved_by"], ["users.id"], ondelete="SET NULL"), sa.ForeignKeyConstraint(["verification_id"], ["verifications.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("case_number"))
    for name, column in [("case_number", "case_number"), ("verification_id", "verification_id"), ("assigned_to", "assigned_to"), ("assigned_supervisor", "assigned_supervisor"), ("created_by", "created_by")]: op.create_index(f"ix_cases_{name}", "cases", [column], unique=False)
    op.create_table("case_evidence", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("case_id", sa.Uuid(), nullable=False), sa.Column("evidence_type", sa.String(64), nullable=False), sa.Column("source_type", sa.String(64), nullable=False), sa.Column("source_id", sa.Uuid(), nullable=False), sa.Column("title", sa.String(180), nullable=False), sa.Column("summary", sa.String(), nullable=False), sa.Column("severity", sa.String(16), nullable=False), sa.Column("created_by", sa.Uuid(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_case_evidence_case_id", "case_evidence", ["case_id"], unique=False); op.create_index("ix_case_evidence_source_id", "case_evidence", ["source_id"], unique=False)
    op.create_table("case_notes", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("case_id", sa.Uuid(), nullable=False), sa.Column("author_id", sa.Uuid(), nullable=False), sa.Column("body", sa.String(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_case_notes_case_id", "case_notes", ["case_id"], unique=False)
    op.create_table("case_decisions", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("case_id", sa.Uuid(), nullable=False), sa.Column("decision", sa.String(16), nullable=False), sa.Column("reason", sa.String(), nullable=False), sa.Column("decided_by", sa.Uuid(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["decided_by"], ["users.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_case_decisions_case_id", "case_decisions", ["case_id"], unique=False)
    op.add_column("audit_events", sa.Column("case_id", sa.Uuid(), nullable=True)); op.create_foreign_key("fk_audit_events_case_id", "audit_events", "cases", ["case_id"], ["id"], ondelete="SET NULL"); op.create_index("ix_audit_events_case_id", "audit_events", ["case_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_events_case_id", table_name="audit_events"); op.drop_constraint("fk_audit_events_case_id", "audit_events", type_="foreignkey"); op.drop_column("audit_events", "case_id")
    op.drop_index("ix_case_decisions_case_id", table_name="case_decisions"); op.drop_table("case_decisions")
    op.drop_index("ix_case_notes_case_id", table_name="case_notes"); op.drop_table("case_notes")
    op.drop_index("ix_case_evidence_source_id", table_name="case_evidence"); op.drop_index("ix_case_evidence_case_id", table_name="case_evidence"); op.drop_table("case_evidence")
    for name in ["created_by", "assigned_supervisor", "assigned_to", "verification_id", "case_number"]: op.drop_index(f"ix_cases_{name}", table_name="cases")
    op.drop_table("cases")
