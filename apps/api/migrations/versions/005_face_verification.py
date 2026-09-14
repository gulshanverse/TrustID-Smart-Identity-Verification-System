"""add face verification persistence

Revision ID: 005_face_verification
Revises: 004_tampering_detection
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "005_face_verification"
down_revision: str | None = "004_tampering_detection"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table("face_verifications", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("verification_id", sa.Uuid(), nullable=False), sa.Column("document_id", sa.Uuid(), nullable=False), sa.Column("status", sa.String(length=32), nullable=False), sa.Column("outcome", sa.String(length=32), nullable=False), sa.Column("similarity_score", sa.Float(), nullable=True), sa.Column("confidence", sa.Float(), nullable=True), sa.Column("provider", sa.String(length=128), nullable=False), sa.Column("provider_version", sa.String(length=64), nullable=False), sa.Column("summary", sa.String(), nullable=False), sa.Column("failure_reason", sa.String(), nullable=True), sa.Column("document_face_quality", sa.String(length=32), nullable=False), sa.Column("presented_face_quality", sa.String(length=32), nullable=False), sa.Column("face_count", sa.Integer(), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["verification_id"], ["verifications.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_face_verifications_verification_id", "face_verifications", ["verification_id"], unique=False)
    op.create_index("ix_face_verifications_document_id", "face_verifications", ["document_id"], unique=False)
    op.create_table("face_verification_evidence", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("face_verification_id", sa.Uuid(), nullable=False), sa.Column("name", sa.String(length=64), nullable=False), sa.Column("value", sa.String(length=160), nullable=False), sa.Column("explanation", sa.String(), nullable=False), sa.ForeignKeyConstraint(["face_verification_id"], ["face_verifications.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_face_verification_evidence_face_verification_id", "face_verification_evidence", ["face_verification_id"], unique=False)
    op.add_column("audit_events", sa.Column("face_verification_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_audit_events_face_verification_id", "audit_events", "face_verifications", ["face_verification_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_audit_events_face_verification_id", "audit_events", ["face_verification_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_events_face_verification_id", table_name="audit_events")
    op.drop_constraint("fk_audit_events_face_verification_id", "audit_events", type_="foreignkey")
    op.drop_column("audit_events", "face_verification_id")
    op.drop_index("ix_face_verification_evidence_face_verification_id", table_name="face_verification_evidence")
    op.drop_table("face_verification_evidence")
    op.drop_index("ix_face_verifications_document_id", table_name="face_verifications")
    op.drop_index("ix_face_verifications_verification_id", table_name="face_verifications")
    op.drop_table("face_verifications")
