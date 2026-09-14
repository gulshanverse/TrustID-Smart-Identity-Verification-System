"""add OCR result persistence

Revision ID: 003_ocr_extraction
Revises: 002_document_ingestion
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003_ocr_extraction"
down_revision: str | None = "002_document_ingestion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ocr_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("raw_text", sa.String(), nullable=False),
        sa.Column("language", sa.String(length=32), nullable=False),
        sa.Column("overall_confidence", sa.Float(), nullable=False),
        sa.Column("provider", sa.String(length=128), nullable=False),
        sa.Column("provider_version", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ocr_results_document_id", "ocr_results", ["document_id"], unique=False)
    op.add_column("audit_events", sa.Column("ocr_result_id", sa.Uuid(), nullable=True))
    op.add_column("audit_events", sa.Column("provider", sa.String(length=128), nullable=True))
    op.create_foreign_key("fk_audit_events_ocr_result_id", "audit_events", "ocr_results", ["ocr_result_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_audit_events_ocr_result_id", "audit_events", ["ocr_result_id"], unique=False)
    op.create_table(
        "ocr_fields",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ocr_result_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("normalized_value", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("source_text", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["ocr_result_id"], ["ocr_results.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ocr_fields_ocr_result_id", "ocr_fields", ["ocr_result_id"], unique=False)
    op.create_table(
        "ocr_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ocr_field_id", sa.Uuid(), nullable=False),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("text", sa.String(), nullable=True),
        sa.Column("start_offset", sa.Integer(), nullable=True),
        sa.Column("end_offset", sa.Integer(), nullable=True),
        sa.Column("line_index", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["ocr_field_id"], ["ocr_fields.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ocr_evidence_ocr_field_id", "ocr_evidence", ["ocr_field_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_events_ocr_result_id", table_name="audit_events")
    op.drop_constraint("fk_audit_events_ocr_result_id", "audit_events", type_="foreignkey")
    op.drop_column("audit_events", "provider")
    op.drop_column("audit_events", "ocr_result_id")
    op.drop_index("ix_ocr_evidence_ocr_field_id", table_name="ocr_evidence")
    op.drop_table("ocr_evidence")
    op.drop_index("ix_ocr_fields_ocr_result_id", table_name="ocr_fields")
    op.drop_table("ocr_fields")
    op.drop_index("ix_ocr_results_document_id", table_name="ocr_results")
    op.drop_table("ocr_results")
