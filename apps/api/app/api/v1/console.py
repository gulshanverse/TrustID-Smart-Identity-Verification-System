from fastapi import APIRouter, Depends

from app.api.dependencies import require_permission
from app.domain.auth import Permission
from app.services.auth_service import AuthUser

router = APIRouter(prefix="/console", tags=["console"])


@router.get("/access")
def console_access(user: AuthUser = Depends(require_permission(Permission.CONSOLE_ACCESS))) -> dict[str, str]:
    return {"status": "authorized", "user_id": str(user.id)}


@router.get("/audit")
def audit_access(user: AuthUser = Depends(require_permission(Permission.AUDIT))) -> dict[str, str]:
    return {"status": "authorized", "user_id": str(user.id)}
