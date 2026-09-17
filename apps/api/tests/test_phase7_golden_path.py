import importlib
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_auth_service
from app.db.models import AuditEventModel, Base
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
