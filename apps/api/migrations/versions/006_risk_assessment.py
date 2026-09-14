"""add document validation and risk assessment persistence

Revision ID: 006_risk_assessment
Revises: 005_face_verification
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "006_risk_assessment"
down_revision: str | None = "005_face_verification"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table("document_validations", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("document_id", sa.Uuid(), nullable=False), sa.Column("status", sa.String(length=32), nullable=False), sa.Column("provider", sa.String(length=128), nullable=False), sa.Column("provider_version", sa.String(length=64), nullable=False), sa.Column("summary", sa.String(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_document_validations_document_id", "document_validations", ["document_id"], unique=False)
    op.create_table("document_validation_findings", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("validation_id", sa.Uuid(), nullable=False), sa.Column("name", sa.String(length=64), nullable=False), sa.Column("severity", sa.String(length=16), nullable=False), sa.Column("passed", sa.Boolean(), nullable=False), sa.Column("explanation", sa.String(), nullable=False), sa.Column("reference", sa.String(length=160), nullable=True), sa.ForeignKeyConstraint(["validation_id"], ["document_validations.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_document_validation_findings_validation_id", "document_validation_findings", ["validation_id"], unique=False)
    op.create_table("risk_assessments", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("verification_id", sa.Uuid(), nullable=False), sa.Column("status", sa.String(length=32), nullable=False), sa.Column("risk_score", sa.Integer(), nullable=False), sa.Column("risk_level", sa.String(length=16), nullable=False), sa.Column("recommendation", sa.String(), nullable=False), sa.Column("confidence", sa.Float(), nullable=True), sa.Column("summary", sa.String(), nullable=False), sa.Column("assessment_version", sa.String(length=32), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["verification_id"], ["verifications.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_risk_assessments_verification_id", "risk_assessments", ["verification_id"], unique=False)
    op.create_table("risk_factors", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("risk_assessment_id", sa.Uuid(), nullable=False), sa.Column("factor_name", sa.String(length=128), nullable=False), sa.Column("source_module", sa.String(length=64), nullable=False), sa.Column("severity", sa.String(length=16), nullable=False), sa.Column("contribution", sa.Integer(), nullable=False), sa.Column("explanation", sa.String(), nullable=False), sa.Column("evidence_reference", sa.String(length=160), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["risk_assessment_id"], ["risk_assessments.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_risk_factors_risk_assessment_id", "risk_factors", ["risk_assessment_id"], unique=False)
    op.add_column("audit_events", sa.Column("validation_id", sa.Uuid(), nullable=True))
    op.add_column("audit_events", sa.Column("risk_assessment_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_audit_events_validation_id", "audit_events", "document_validations", ["validation_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_audit_events_risk_assessment_id", "audit_events", "risk_assessments", ["risk_assessment_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_audit_events_validation_id", "audit_events", ["validation_id"], unique=False)
    op.create_index("ix_audit_events_risk_assessment_id", "audit_events", ["risk_assessment_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_events_risk_assessment_id", table_name="audit_events")
    op.drop_index("ix_audit_events_validation_id", table_name="audit_events")
    op.drop_constraint("fk_audit_events_risk_assessment_id", "audit_events", type_="foreignkey")
    op.drop_constraint("fk_audit_events_validation_id", "audit_events", type_="foreignkey")
    op.drop_column("audit_events", "risk_assessment_id")
    op.drop_column("audit_events", "validation_id")
    op.drop_index("ix_risk_factors_risk_assessment_id", table_name="risk_factors")
    op.drop_table("risk_factors")
    op.drop_index("ix_risk_assessments_verification_id", table_name="risk_assessments")
    op.drop_table("risk_assessments")
    op.drop_index("ix_document_validation_findings_validation_id", table_name="document_validation_findings")
    op.drop_table("document_validation_findings")
    op.drop_index("ix_document_validations_document_id", table_name="document_validations")
    op.drop_table("document_validations")
