import importlib
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_auth_service
from app.db.models import AuditEventModel, Base, OCRFieldModel, OCRResultModel
from app.db.session import get_db
from app.domain.auth import Role
from app.domain.documents import InMemoryObjectStorage
from app.main import app
from app.services.auth_service import AuthService


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)


@pytest.fixture
def client(db: Session, monkeypatch: pytest.MonkeyPatch):
    auth = AuthService(db)
    auth.add_user("golden@example.test", "Golden Officer", "correct horse battery", {Role.OFFICER})
    storage = InMemoryObjectStorage()
    main_module = importlib.import_module("app.main")
    monkeypatch.setattr(main_module, "storage", storage)
    app.dependency_overrides[get_auth_service] = lambda: auth
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client, db
    app.dependency_overrides.clear()


def test_http_golden_path_reaches_officer_decision(client) -> None:
    test_client, db = client
    login = test_client.post("/api/v1/auth/login", json={"identifier": "golden@example.test", "password": "correct horse battery"})
    assert login.status_code == 200
    verification = test_client.post("/api/v1/verifications")
    assert verification.status_code == 201
    verification_id = verification.json()["id"]
    document = test_client.post(
        f"/api/v1/verifications/{verification_id}/documents",
        data={"document_type": "PASSPORT"},
        files={"file": ("golden.pdf", b"%PDF-1.7\nTRUSTID-DEMO-OCR: fictional\nTRUSTID-TAMPERING:CLEAN\nTRUSTID-FACE:DOCUMENT", "application/pdf")},
    )
    assert document.status_code == 201
    document_id = document.json()["id"]
    assert test_client.post(f"/api/v1/documents/{document_id}/ocr").status_code == 201
    assert test_client.post(f"/api/v1/documents/{document_id}/tampering", json={"scenario": "CLEAN"}).status_code == 201
    face = test_client.post(
        f"/api/v1/documents/{document_id}/face-verification",
        data={"scenario": "MATCH"},
        files={"image": ("face.jpg", b"\xff\xd8\xffTRUSTID-FACE:MATCH\nDEMO / SIMULATED\nFICTIONAL SAMPLE", "image/jpeg")},
    )
    assert face.status_code == 201
    analysis = test_client.post(f"/api/v1/verifications/{verification_id}/analyze")
    assert analysis.status_code == 201
    assert analysis.json()["status"] == "COMPLETED"
    assert test_client.get(f"/api/v1/verifications/{verification_id}/result").status_code == 200
    case = test_client.post("/api/v1/cases", json={"verification_id": verification_id, "title": "Golden path review", "description": "DEMO / SIMULATED officer review"})
    assert case.status_code == 201
    decision = test_client.post(f"/api/v1/cases/{case.json()['id']}/decision", json={"decision": "APPROVE", "reason": "Reviewed the complete deterministic demo evidence."})
    assert decision.status_code == 200
    events = db.scalars(select(AuditEventModel).where(AuditEventModel.verification_id == UUID(verification_id))).all()
    event_types = {event.event_type for event in events}
    assert "VERIFICATION_ANALYSIS_COMPLETED" in event_types
    assert "VERIFICATION_CORRELATION_COMPLETED" in event_types
    assert "CASE_DECISION_RECORDED" in event_types


def test_cross_document_findings_survive_all_read_paths(client) -> None:
    test_client, db = client
    assert test_client.post("/api/v1/auth/login", json={"identifier": "golden@example.test", "password": "correct horse battery"}).status_code == 200
    verification_id = test_client.post("/api/v1/verifications").json()["id"]
    documents = []
    for filename in ("first.pdf", "second.pdf"):
        response = test_client.post(
            f"/api/v1/verifications/{verification_id}/documents",
            data={"document_type": "PASSPORT"},
            files={"file": (filename, b"%PDF-1.7\nTRUSTID-DEMO-OCR: fictional", "application/pdf")},
        )
        assert response.status_code == 201
        documents.append(response.json()["id"])
        assert test_client.post(f"/api/v1/documents/{documents[-1]}/ocr").status_code == 201

    second_result = db.scalar(select(OCRResultModel).where(OCRResultModel.document_id == UUID(documents[1])))
    assert second_result is not None
    second_fields = {field.name: field for field in second_result.fields}
    second_fields["full_name"].value = "DIFFERENT APPLICANT"
    second_fields["full_name"].normalized_value = "DIFFERENT APPLICANT"
    second_fields["date_of_birth"].value = "1999-01-01"
    second_fields["date_of_birth"].normalized_value = "1999-01-01"
    second_fields["expiry_date"].value = "2029-01-01"
    second_fields["expiry_date"].normalized_value = "2029-01-01"
    db.add(OCRFieldModel(ocr_result_id=second_result.id, name="visa_reference", value="REF-999", normalized_value="REF-999", confidence=0.97, source_text="REF-999"))
    first_result = db.scalar(select(OCRResultModel).where(OCRResultModel.document_id == UUID(documents[0])))
    assert first_result is not None
    db.add(OCRFieldModel(ocr_result_id=first_result.id, name="visa_reference", value="REF-123", normalized_value="REF-123", confidence=0.97, source_text="REF-123"))
    db.commit()

    analysis = test_client.post(f"/api/v1/verifications/{verification_id}/analyze")
    assert analysis.status_code == 201
    analysis_findings = {item["code"]: item for item in analysis.json()["cross_document_findings"] if item["status"] == "NO_MATCH"}
    assert set(analysis_findings) == {"CROSS_DOCUMENT_NAME_MISMATCH", "CROSS_DOCUMENT_DOB_MISMATCH", "CROSS_DOCUMENT_REFERENCE_MISMATCH", "CROSS_DOCUMENT_VALIDITY_CONFLICT"}
    assert all(item["severity"] == "MEDIUM" and "review" in item["explanation"].lower() for item in analysis_findings.values())
    assert all(factor["contribution"] >= 0 for factor in analysis.json()["risk"]["factors"])

    result = test_client.get(f"/api/v1/verifications/{verification_id}/result")
    summary = test_client.get(f"/api/v1/verifications/{verification_id}/phase8-summary")
    intelligence = test_client.get(f"/api/v1/verifications/{verification_id}/decision-intelligence")
    assert result.status_code == summary.status_code == intelligence.status_code == 200
    assert {item["code"] for item in result.json()["cross_document_findings"] if item["status"] == "NO_MATCH"} == set(analysis_findings)
    assert {item["code"] for item in summary.json()["cross_document_findings"] if item["status"] == "NO_MATCH"} == set(analysis_findings)
    contradictions = {item["code"] for item in intelligence.json()["contradictions"]}
    assert set(analysis_findings) <= contradictions
    risk_context = intelligence.json()["risk_context"]
    assert risk_context["score"] == sum(factor["contribution"] for factor in risk_context["factors"])
    assert result.json()["cross_document_findings"] == test_client.get(f"/api/v1/verifications/{verification_id}/result").json()["cross_document_findings"]


def test_phase8_summary_result_and_decision_intelligence_are_owner_scoped(client) -> None:
    test_client, db = client
    AuthService(db).add_user("other@example.test", "Other Officer", "other password", {Role.OFFICER})
    assert test_client.post("/api/v1/auth/login", json={"identifier": "other@example.test", "password": "other password"}).status_code == 200
    other_verification = test_client.post("/api/v1/verifications").json()["id"]
    other_document = test_client.post(
        f"/api/v1/verifications/{other_verification}/documents",
        data={"document_type": "PASSPORT"},
        files={"file": ("other.pdf", b"%PDF-1.7\nTRUSTID-DEMO-OCR: other", "application/pdf")},
    )
    assert other_document.status_code == 201
    assert test_client.post("/api/v1/auth/logout").status_code == 200
    assert test_client.post("/api/v1/auth/login", json={"identifier": "golden@example.test", "password": "correct horse battery"}).status_code == 200
    for path in ("phase8-summary", "result", "decision-intelligence"):
        response = test_client.get(f"/api/v1/verifications/{other_verification}/{path}")
        assert response.status_code == 404
        assert "other" not in response.text.lower()
