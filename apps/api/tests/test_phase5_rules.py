from datetime import date
from uuid import uuid4

from app.domain.documents import DocumentType
from app.domain.external_verification import (
    ExternalStatus,
    ExternalVerificationQuery,
    MockExternalVerificationProvider,
    ProductionExternalVerificationProvider,
)
from app.domain.ocr import OCRField, OCRResult, OCRStatus
from app.domain.rules import FixedClock, RulesEngine, RuleStatus, ValidityStatus, evaluate_validity


def ocr(document_id, fields):
    return OCRResult(
        uuid4(),
        document_id,
        OCRStatus.COMPLETED,
        "",
        "en",
        0.99,
        "test",
        "1",
        tuple(fields),
        "2026-01-01T00:00:00+00:00",
        "2026-01-01T00:00:00+00:00",
    )


def test_validity_outcomes_are_explicit_and_deterministic():
    today = date(2026, 9, 17)
    assert evaluate_validity("2026-09-17", today) == ValidityStatus.VALID
    assert evaluate_validity("2026-09-18", today) == ValidityStatus.NOT_YET_VALID
    assert evaluate_validity("not-a-date", today) == ValidityStatus.INVALID_DATE
    assert evaluate_validity(None, today) == ValidityStatus.NOT_AVAILABLE


def test_valid_passport_rules_are_repeatable():
    document_id = uuid4()
    fields = [
        OCRField(name, value, value, 0.99, value)
        for name, value in (
            ("full_name", "FICTIONAL"),
            ("passport_number", "AB123456"),
            ("nationality", "X"),
            ("date_of_birth", "1990-01-01"),
            ("expiry_date", "2030-01-01"),
        )
    ]
    result = ocr(document_id, fields)
    engine = RulesEngine(FixedClock(date(2026, 9, 17)))
    first = engine.evaluate(DocumentType.PASSPORT, result)
    second = engine.evaluate(DocumentType.PASSPORT, result)
    assert [(item.rule_id, item.status) for item in first] == [
        (item.rule_id, item.status) for item in second
    ]
    assert all(item.status != RuleStatus.FAIL for item in first)


def test_expired_passport_and_missing_field_are_explained():
    result = ocr(
        uuid4(),
        [
            OCRField("passport_number", "BAD", "BAD", 0.99, "BAD"),
            OCRField("expiry_date", "2020-01-01", "2020-01-01", 0.99, "2020-01-01"),
        ],
    )
    rules = RulesEngine(FixedClock(date(2026, 9, 17))).evaluate(DocumentType.PASSPORT, result)
    assert any(
        item.rule_id == "PASSPORT_EXPIRY_VALIDITY" and item.status == RuleStatus.FAIL
        for item in rules
    )
    assert any(
        item.rule_id == "PASSPORT_REQUIRED_FULL_NAME" and item.status == RuleStatus.FAIL
        for item in rules
    )


def test_external_statuses_are_not_conflated():
    query = ExternalVerificationQuery(DocumentType.PASSPORT, "SYNTHETIC-1")
    demo = MockExternalVerificationProvider({"SYNTHETIC-1": ExternalStatus.VERIFIED}).verify(query)
    production = ProductionExternalVerificationProvider().verify(query)
    assert demo.status == ExternalStatus.VERIFIED and demo.demo is True
    assert production.status == ExternalStatus.NOT_AVAILABLE and production.demo is False
