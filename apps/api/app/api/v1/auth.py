import logging

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.exceptions import HTTPException

from app.api.auth_schemas import LoginRequest, LoginResponse, LogoutResponse, SafeUser
from app.api.dependencies import get_auth_service, get_current_user
from app.core.config import get_settings
from app.services.auth_service import AuthService, AuthUser

logger = logging.getLogger("trustid.auth")
router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, response: Response, service: AuthService = Depends(get_auth_service)) -> LoginResponse:
    user = service.authenticate(payload.identifier, payload.password)
    if user is None:
        logger.warning("login_failure")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    token = service.create_session(user)
    settings = get_settings()
    response.set_cookie(settings.session_cookie_name, token, httponly=True, secure=settings.session_cookie_secure, samesite=settings.session_cookie_samesite, max_age=settings.session_cookie_max_age, path="/")
    logger.info("login_success", extra={"user_id": str(user.id)})
    return LoginResponse(user=service.to_safe_user(user))


@router.post("/logout", response_model=LogoutResponse)
def logout(response: Response, request: Request, service: AuthService = Depends(get_auth_service)) -> LogoutResponse:
    settings = get_settings()
    service.revoke_session(request.cookies.get(settings.session_cookie_name))
    response.delete_cookie(settings.session_cookie_name)
    logger.info("logout")
    return LogoutResponse(status="signed_out")


@router.get("/me", response_model=SafeUser)
def me(user: AuthUser = Depends(get_current_user), service: AuthService = Depends(get_auth_service)) -> SafeUser:
    return service.to_safe_user(user)
