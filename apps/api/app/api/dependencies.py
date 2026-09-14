from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status

from app.core.config import get_settings
from app.domain.auth import Permission
from app.services.auth_service import AuthService, AuthUser, auth_service


def get_auth_service() -> AuthService:
    return auth_service


def get_current_user(request: Request, service: AuthService = Depends(get_auth_service)) -> AuthUser:
    session = request.cookies.get(get_settings().session_cookie_name)
    user = service.get_user_by_session(session)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return user


def require_permission(permission: Permission) -> Callable[..., AuthUser]:
    def dependency(user: AuthUser = Depends(get_current_user), service: AuthService = Depends(get_auth_service)) -> AuthUser:
        if not service.has_permission(user, permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to perform this action.")
        return user

    return dependency
