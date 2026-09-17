from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import User
from app.db.session import get_db
from app.domain.auth import Permission
from app.services.auth_service import AuthService, AuthUser


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


def reconcile_persistent_identity(user: AuthUser, db: Session) -> AuthUser:
    """Use the durable database identity when in-process auth has restarted."""
    persistent = db.get(User, user.id)
    if persistent is None:
        normalized_email = user.email.strip().lower()
        persistent = db.scalar(select(User).where(User.email == normalized_email))
    if persistent is not None:
        user.id = persistent.id
    return user


def get_current_user(request: Request, service: AuthService = Depends(get_auth_service), db: Session = Depends(get_db)) -> AuthUser:
    session = request.cookies.get(get_settings().session_cookie_name)
    user = service.get_user_by_session(session)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    user = reconcile_persistent_identity(user, db)
    service.rebind_session(session, user.id)
    return user


def require_permission(permission: Permission) -> Callable[..., AuthUser]:
    def dependency(user: AuthUser = Depends(get_current_user), service: AuthService = Depends(get_auth_service)) -> AuthUser:
        if not service.has_permission(user, permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to perform this action.")
        return user

    return dependency
