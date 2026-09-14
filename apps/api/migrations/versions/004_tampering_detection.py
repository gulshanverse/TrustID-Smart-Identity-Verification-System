"""add tampering detection persistence

Revision ID: 004_tampering_detection
Revises: 003_ocr_extraction
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "004_tampering_detection"
down_revision: str | None = "003_ocr_extraction"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table("tampering_results", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("document_id", sa.Uuid(), nullable=False), sa.Column("status", sa.String(length=32), nullable=False), sa.Column("technical_signal_score", sa.Float(), nullable=False), sa.Column("overall_confidence", sa.Float(), nullable=False), sa.Column("provider", sa.String(length=128), nullable=False), sa.Column("provider_version", sa.String(length=64), nullable=False), sa.Column("summary", sa.String(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_tampering_results_document_id", "tampering_results", ["document_id"], unique=False)
    op.create_table("tampering_findings", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("tampering_result_id", sa.Uuid(), nullable=False), sa.Column("finding_type", sa.String(length=64), nullable=False), sa.Column("severity", sa.String(length=16), nullable=False), sa.Column("confidence", sa.Float(), nullable=False), sa.Column("title", sa.String(length=240), nullable=False), sa.Column("description", sa.String(), nullable=False), sa.Column("related_ocr_field", sa.String(length=64), nullable=True), sa.ForeignKeyConstraint(["tampering_result_id"], ["tampering_results.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_tampering_findings_tampering_result_id", "tampering_findings", ["tampering_result_id"], unique=False)
    op.create_table("tampering_evidence", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("tampering_finding_id", sa.Uuid(), nullable=False), sa.Column("evidence_type", sa.String(length=64), nullable=False), sa.Column("page", sa.Integer(), nullable=True), sa.Column("region", sa.String(length=160), nullable=True), sa.Column("description", sa.String(), nullable=False), sa.Column("source_reference", sa.String(length=160), nullable=True), sa.Column("technical_signal", sa.String(length=160), nullable=False), sa.Column("confidence", sa.Float(), nullable=False), sa.ForeignKeyConstraint(["tampering_finding_id"], ["tampering_findings.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_tampering_evidence_tampering_finding_id", "tampering_evidence", ["tampering_finding_id"], unique=False)
    op.add_column("audit_events", sa.Column("tampering_result_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_audit_events_tampering_result_id", "audit_events", "tampering_results", ["tampering_result_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_audit_events_tampering_result_id", "audit_events", ["tampering_result_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_events_tampering_result_id", table_name="audit_events")
    op.drop_constraint("fk_audit_events_tampering_result_id", "audit_events", type_="foreignkey")
    op.drop_column("audit_events", "tampering_result_id")
    op.drop_index("ix_tampering_evidence_tampering_finding_id", table_name="tampering_evidence")
    op.drop_table("tampering_evidence")
    op.drop_index("ix_tampering_findings_tampering_result_id", table_name="tampering_findings")
    op.drop_table("tampering_findings")
    op.drop_index("ix_tampering_results_document_id", table_name="tampering_results")
    op.drop_table("tampering_results")
