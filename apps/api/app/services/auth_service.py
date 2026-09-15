import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.api.auth_schemas import SafeUser
from app.core.config import get_settings
from app.core.passwords import hash_password, verify_password
from app.domain.auth import Permission, Role, permissions_for_roles


@dataclass
class AuthUser:
    id: UUID
    email: str
    display_name: str
    password_hash: str
    roles: set[Role]
    is_active: bool = True
    last_login_at: datetime | None = None


class AuthService:
    """Provider-neutral auth service; persistence can be swapped for SQLAlchemy repository."""

    def __init__(self) -> None:
        self._users: dict[str, AuthUser] = {}
        self._sessions: dict[str, UUID] = {}
        self._seed_from_environment()

    def _seed_from_environment(self) -> None:
        settings = get_settings()
        if not settings.demo_password:
            return
        for email, name, role in (
            ("demo.officer@trustid.local", "Demo Officer", Role.OFFICER),
            ("demo.supervisor@trustid.local", "Demo Supervisor", Role.SUPERVISOR),
            ("demo.auditor@trustid.local", "Demo Auditor", Role.AUDITOR),
            ("demo.admin@trustid.local", "Demo Administrator", Role.ADMIN),
        ):
            self._users[email] = AuthUser(uuid4(), email, name, hash_password(settings.demo_password), {role})

    def add_user(self, email: str, display_name: str, password: str, roles: set[Role], is_active: bool = True) -> AuthUser:
        key = email.strip().lower()
        if key in self._users:
            raise ValueError("User already exists.")
        user = AuthUser(uuid4(), key, display_name, hash_password(password), roles, is_active)
        self._users[key] = user
        return user

    def authenticate(self, identifier: str, password: str) -> AuthUser | None:
        user = self._users.get(identifier.strip().lower())
        if user is None or not user.is_active or not verify_password(password, user.password_hash):
            return None
        user.last_login_at = datetime.now(UTC)
        return user

    def create_session(self, user: AuthUser) -> str:
        token = secrets.token_urlsafe(32)
        self._sessions[token] = user.id
        return token

    def get_user_by_session(self, token: str | None) -> AuthUser | None:
        if not token:
            return None
        user_id = self._sessions.get(token)
        return next((user for user in self._users.values() if user.id == user_id and user.is_active), None)

    def revoke_session(self, token: str | None) -> None:
        if token:
            self._sessions.pop(token, None)

    def rebind_session(self, token: str | None, user_id: UUID) -> None:
        if token:
            self._sessions[token] = user_id

    def to_safe_user(self, user: AuthUser) -> SafeUser:
        permissions = sorted(permissions_for_roles(user.roles), key=lambda permission: permission.value)
        return SafeUser(id=user.id, email=user.email, display_name=user.display_name, roles=sorted(user.roles, key=lambda role: role.value), permissions=permissions, is_active=user.is_active)

    def has_permission(self, user: AuthUser, permission: Permission) -> bool:
        return permission in permissions_for_roles(user.roles)


auth_service = AuthService()
