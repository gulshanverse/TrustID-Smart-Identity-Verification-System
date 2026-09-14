from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.auth import Permission, Role


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class SafeUser(BaseModel):
    id: UUID
    email: str
    display_name: str
    roles: list[Role]
    permissions: list[Permission]
    is_active: bool


class LoginResponse(BaseModel):
    user: SafeUser


class LogoutResponse(BaseModel):
    status: str
