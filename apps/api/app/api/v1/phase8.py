from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.api.v1.intelligence import latest_result
from app.db.session import get_db
from app.domain.advanced_document_intelligence import advanced_forensics_boundary, liveness_boundary
from app.domain.auth import Permission
from app.services.auth_service import AuthUser

router = APIRouter(prefix="/verifications", tags=["phase-8"])


@router.get("/{verification_id}/phase8-summary")
def phase8_summary(
    verification_id: UUID,
    user: AuthUser = Depends(require_permission(Permission.DOCUMENT_READ)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    result = latest_result(verification_id, user, db)
    return {
        "verification_id": str(verification_id),
        "status": result.status,
        "risk": result.risk.model_dump(mode="json"),
        "evidence": [item.model_dump(mode="json") for item in result.evidence],
        "findings": [item.model_dump(mode="json") for item in result.findings],
        "cross_document_findings": [item.model_dump(mode="json") for item in result.cross_document_findings],
        "capabilities": {
            "advanced_document_intelligence": "DETERMINISTIC_RULES",
            "cross_document_correlation": "SUPPORTED_FIELDS_ONLY",
            "advanced_forensics": advanced_forensics_boundary(),
            "liveness": liveness_boundary(),
        },
        "advisory_boundary": "Decision Intelligence and all new findings require authorized officer review; risk remains authoritative.",
    }
