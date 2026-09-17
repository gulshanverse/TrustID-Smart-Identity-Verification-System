from fastapi.testclient import TestClient

import app.api.v1.health as health_module
from app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "trustid-api"
    assert "X-Request-ID" in response.headers


class _ReadySession:
    def execute(self, _query: object) -> None:
        return None

    def close(self) -> None:
        return None


def test_readiness_checks_required_database_without_leaking_details(monkeypatch) -> None:
    monkeypatch.setattr(health_module, "SessionLocal", lambda: _ReadySession())
    response = client.get("/api/v1/readiness")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["checks"] == {"database": "ok"}


def test_readiness_does_not_expose_dependency_exception(monkeypatch) -> None:
    class BrokenSession(_ReadySession):
        def execute(self, _query: object) -> None:
            raise RuntimeError("postgres://secret-password@internal.example")

    monkeypatch.setattr(health_module, "SessionLocal", lambda: BrokenSession())
    response = client.get("/api/v1/readiness")
    assert response.status_code == 503
    assert response.json()["detail"] == "Service dependencies are not ready."
    assert "secret-password" not in response.text
