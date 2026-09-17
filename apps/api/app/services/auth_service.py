from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.api.auth_schemas import SafeUser
from app.core.config import get_settings
from app.core.passwords import hash_password, verify_password
from app.db.models import AuthSessionModel, RoleModel, User
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
    """Database-backed authentication in API mode; memory mode is retained for isolated tests."""

    def __init__(self, db: Session | None = None) -> None:
        self.db = db
        self._users: dict[str, AuthUser] = {}
        self._sessions: dict[str, UUID] = {}
        if db is None:
            self._seed_from_environment()
        else:
            self._seed_persistent_from_environment()

    @staticmethod
    def _demo_accounts() -> tuple[tuple[str, str, Role], ...]:
        return (
            ("demo.officer@trustid.local", "Demo Officer", Role.OFFICER),
            ("demo.supervisor@trustid.local", "Demo Supervisor", Role.SUPERVISOR),
            ("demo.auditor@trustid.local", "Demo Auditor", Role.AUDITOR),
            ("demo.admin@trustid.local", "Demo Administrator", Role.ADMIN),
        )

    def _seed_from_environment(self) -> None:
        settings = get_settings()
        if settings.demo_password:
            for email, name, role in self._demo_accounts():
                self._users[email] = AuthUser(uuid4(), email, name, hash_password(settings.demo_password), {role})

    def _seed_persistent_from_environment(self) -> None:
        settings = get_settings()
        if not settings.demo_password or self.db is None:
            return
        changed = False
        for email, name, role in self._demo_accounts():
            user = self.db.scalar(select(User).where(User.email == email).options(selectinload(User.roles)))
            role_model = self.db.scalar(select(RoleModel).where(RoleModel.name == role.value))
            if role_model is None:
                role_model = RoleModel(name=role.value)
                self.db.add(role_model)
                self.db.flush()
                changed = True
            if user is None:
                self.db.add(User(email=email, display_name=name, password_hash=hash_password(settings.demo_password), roles=[role_model]))
                changed = True
            elif role_model not in user.roles:
                user.roles.append(role_model)
                changed = True
        if changed:
            self.db.commit()

    def add_user(self, email: str, display_name: str, password: str, roles: set[Role], is_active: bool = True) -> AuthUser:
        key = email.strip().lower()
        if self.db is None:
            if key in self._users:
                raise ValueError("User already exists.")
            user = AuthUser(uuid4(), key, display_name, hash_password(password), roles, is_active)
            self._users[key] = user
            return user
        if self.db.scalar(select(User).where(User.email == key)) is not None:
            raise ValueError("User already exists.")
        role_models: list[RoleModel] = []
        for role in roles:
            role_model = self.db.scalar(select(RoleModel).where(RoleModel.name == role.value))
            if role_model is None:
                role_model = RoleModel(name=role.value)
                self.db.add(role_model)
                self.db.flush()
            role_models.append(role_model)
        persistent_user = User(email=key, display_name=display_name, password_hash=hash_password(password), roles=role_models, is_active=is_active)
        self.db.add(persistent_user)
        self.db.commit()
        self.db.refresh(persistent_user)
        return self._to_auth_user(persistent_user)

    @staticmethod
    def _to_auth_user(user: User) -> AuthUser:
        return AuthUser(user.id, user.email, user.display_name, user.password_hash, {Role(role.name) for role in user.roles}, user.is_active, user.last_login_at)

    def authenticate(self, identifier: str, password: str) -> AuthUser | None:
        key = identifier.strip().lower()
        if self.db is None:
            memory_user = self._users.get(key)
            if memory_user is None:
                return None
            auth_user = memory_user
            persistent_user = None
        else:
            persistent_user = self.db.scalar(select(User).where(User.email == key).options(selectinload(User.roles)))
            if persistent_user is None:
                return None
            auth_user = self._to_auth_user(persistent_user)
        if auth_user is None:
            return None
        if not auth_user.is_active or not verify_password(password, auth_user.password_hash):
            return None
        auth_user.last_login_at = datetime.now(UTC)
        if self.db is not None and persistent_user is not None:
            persistent_user.last_login_at = auth_user.last_login_at
            self.db.commit()
        return auth_user

    def create_session(self, user: AuthUser) -> str:
        token = secrets.token_urlsafe(32)
        if self.db is None:
            self._sessions[token] = user.id
        else:
            expires_at = datetime.now(UTC) + timedelta(seconds=get_settings().session_cookie_max_age)
            self.db.add(AuthSessionModel(token=token, user_id=user.id, expires_at=expires_at))
            self.db.commit()
        return token

    def get_user_by_session(self, token: str | None) -> AuthUser | None:
        if not token:
            return None
        if self.db is None:
            user_id = self._sessions.get(token)
            return next((user for user in self._users.values() if user.id == user_id and user.is_active), None)
        session = self.db.scalar(select(AuthSessionModel).where(AuthSessionModel.token == token))
        expires_at = session.expires_at if session is not None else None
        if expires_at is not None and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if session is None or expires_at is None or expires_at <= datetime.now(UTC):
            if session is not None:
                self.db.delete(session)
                self.db.commit()
            return None
        user = self.db.scalar(select(User).where(User.id == session.user_id).options(selectinload(User.roles)))
        return None if user is None or not user.is_active else self._to_auth_user(user)

    def revoke_session(self, token: str | None) -> None:
        if not token:
            return
        if self.db is None:
            self._sessions.pop(token, None)
        else:
            self.db.execute(delete(AuthSessionModel).where(AuthSessionModel.token == token))
            self.db.commit()

    def rebind_session(self, token: str | None, user_id: UUID) -> None:
        if self.db is None and token:
            self._sessions[token] = user_id

    def to_safe_user(self, user: AuthUser) -> SafeUser:
        permissions = sorted(permissions_for_roles(user.roles), key=lambda permission: permission.value)
        return SafeUser(id=user.id, email=user.email, display_name=user.display_name, roles=sorted(user.roles, key=lambda role: role.value), permissions=permissions, is_active=user.is_active)

    def has_permission(self, user: AuthUser, permission: Permission) -> bool:
        return permission in permissions_for_roles(user.roles)


# Compatibility instance for isolated unit tests; API dependencies construct DB mode per request.
auth_service = AuthService()
