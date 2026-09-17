"""persist phase 5 rule metadata

Revision ID: 011_phase5_rule_metadata
Revises: 010_ocr_intelligence_metadata
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "011_phase5_rule_metadata"
down_revision: str | None = "010_ocr_intelligence_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for name, column in (
        ("rule_id", sa.String(length=128)),
        ("rule_version", sa.String(length=64)),
        ("field", sa.String(length=64)),
        ("observed", sa.String(length=240)),
        ("expected", sa.String(length=240)),
    ):
        op.add_column("document_validation_findings", sa.Column(name, column, nullable=True))


def downgrade() -> None:
    for name in ("expected", "observed", "field", "rule_version", "rule_id"):
        op.drop_column("document_validation_findings", name)
