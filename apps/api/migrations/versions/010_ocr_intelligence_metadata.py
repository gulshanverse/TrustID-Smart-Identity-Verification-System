"""persist OCR quality, MRZ, and field consistency metadata

Revision ID: 010_ocr_intelligence_metadata
Revises: 009_verification_lifecycle
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "010_ocr_intelligence_metadata"
down_revision: str | None = "009_verification_lifecycle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ocr_results", sa.Column("quality", sa.JSON(), nullable=True))
    op.add_column("ocr_results", sa.Column("mrz", sa.JSON(), nullable=True))
    op.add_column("ocr_results", sa.Column("field_consistency", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("ocr_results", "field_consistency")
    op.drop_column("ocr_results", "mrz")
    op.drop_column("ocr_results", "quality")
