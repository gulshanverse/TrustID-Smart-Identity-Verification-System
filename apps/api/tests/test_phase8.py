from __future__ import annotations

from app.domain.advanced_document_intelligence import (
    FindingStatus,
    advanced_forensics_boundary,
    consistency_checks,
    correlate_documents,
    liveness_boundary,
    normalize_field,
)
from app.services.phase8_evaluation import field_metrics, reproducible_report


def test_normalization_preserves_raw_and_unknown_confidence() -> None:
    field = normalize_field("full_name", "  Jane   Doe ")
    assert field.raw_value == "  Jane   Doe "
    assert field.normalized_value == "JANE DOE"
    assert field.confidence is None


def test_consistency_checks_are_deterministic_and_review_oriented() -> None:
    findings = consistency_checks({"date_of_birth": "2099-01-01", "issue_date": "2025-01-01", "expiry_date": "2024-01-01"})
    assert any(item.status == FindingStatus.NO_MATCH for item in findings)
    assert all(item.provenance for item in findings)


def test_cross_document_mismatch_is_not_fraud() -> None:
    findings = correlate_documents([("passport", {"full_name": "Jane Doe", "date_of_birth": "1990-01-01"}), ("visa", {"full_name": "Jane X Doe", "date_of_birth": "1990-01-01"})])
    mismatch = next(item for item in findings if item.field == "full_name")
    assert mismatch.code == "CROSS_DOCUMENT_NAME_MISMATCH"
    assert mismatch.status == FindingStatus.NO_MATCH
    assert "fraud" in mismatch.explanation.lower()


def test_capability_boundaries_are_explicit() -> None:
    assert liveness_boundary()["status"] == "NOT_IMPLEMENTED"
    assert advanced_forensics_boundary()["status"] == "DATASET_VALIDATION_PENDING"


def test_evaluation_is_reproducible_and_handles_empty_data() -> None:
    assert field_metrics([{"expected": "A", "actual": "a"}], "name").accuracy == 1.0
    report = reproducible_report("fixture-v1", [{"field": "name", "expected": "A", "actual": "a"}])
    assert report["status"] == "MEASURED"
    assert report["sample_count"] == 1
    assert reproducible_report("empty", [])["status"] == "DATASET_VALIDATION_PENDING"
