import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_auth_service
from app.core.passwords import hash_password, verify_password
from app.domain.auth import Permission, Role
from app.main import app
from app.services.auth_service import AuthService


@pytest.fixture
def service() -> AuthService:
    auth = AuthService()
    auth.add_user("officer@trustid.local", "Demo Officer", "correct horse battery", {Role.OFFICER})
    auth.add_user("auditor@trustid.local", "Demo Auditor", "correct horse battery", {Role.AUDITOR})
    auth.add_user("inactive@trustid.local", "Inactive User", "correct horse battery", {Role.OFFICER}, is_active=False)
    return auth


@pytest.fixture
def client(service: AuthService):
    app.dependency_overrides[get_auth_service] = lambda: service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def login(client: TestClient, identifier: str = "officer@trustid.local"):
    return client.post("/api/v1/auth/login", json={"identifier": identifier, "password": "correct horse battery"})


def test_password_hashing_is_one_way_and_salted() -> None:
    first = hash_password("correct horse battery")
    second = hash_password("correct horse battery")
    assert first != second
    assert verify_password("correct horse battery", first)
    assert not verify_password("wrong password", first)
    assert "correct horse battery" not in first


def test_login_success_returns_safe_user_and_cookie(client: TestClient) -> None:
    response = login(client)
    assert response.status_code == 200
    assert response.json()["user"]["roles"] == [Role.OFFICER]
    assert "password_hash" not in response.text
    assert "trustid_session=" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]


def test_invalid_and_inactive_login_use_generic_error(client: TestClient) -> None:
    invalid = client.post("/api/v1/auth/login", json={"identifier": "missing@trustid.local", "password": "wrong password"})
    inactive = client.post("/api/v1/auth/login", json={"identifier": "inactive@trustid.local", "password": "correct horse battery"})
    assert invalid.status_code == inactive.status_code == 401
    assert invalid.json()["detail"] == inactive.json()["detail"] == "Invalid credentials."


def test_current_user_logout_and_protected_access(client: TestClient) -> None:
    assert client.get("/api/v1/console/access").status_code == 401
    assert login(client).status_code == 200
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "officer@trustid.local"
    assert client.get("/api/v1/console/access").status_code == 200
    assert client.post("/api/v1/auth/logout").status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/console/access").status_code == 401


def test_role_authorization_is_enforced_server_side(client: TestClient) -> None:
    assert login(client).status_code == 200
    assert client.get("/api/v1/console/audit").status_code == 403
    client.post("/api/v1/auth/logout")
    assert login(client, "auditor@trustid.local").status_code == 200
    assert client.get("/api/v1/console/audit").status_code == 200


def test_duplicate_users_are_rejected(service: AuthService) -> None:
    with pytest.raises(ValueError, match="already exists"):
        service.add_user("OFFICER@trustid.local", "Duplicate", "correct horse battery", {Role.OFFICER})


def test_role_permissions_are_explicit(service: AuthService) -> None:
    officer = service.authenticate("officer@trustid.local", "correct horse battery")
    assert officer is not None
    assert service.has_permission(officer, Permission.VERIFICATION_WORKFLOW)
    assert not service.has_permission(officer, Permission.AUDIT)
