from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TrustID API"
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://trustid:trustid@localhost:5432/trustid"
    redis_url: str = "redis://localhost:6379/0"
    object_storage_endpoint: str = "http://localhost:9000"
    object_storage_region: str = "us-east-1"
    object_storage_bucket: str = "trustid-documents"
    object_storage_access_key: str = "minioadmin"
    object_storage_secret_key: str = "minioadmin"
    ocr_provider: str = "demo"
    tampering_provider: str = "demo"
    face_provider: str = "demo"
    cors_origins: str = "http://localhost:3000"
    demo_password: str | None = None
    session_cookie_name: str = "trustid_session"
    session_cookie_secure: bool = False
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    session_cookie_max_age: int = 28800

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_deployment_security(self) -> "Settings":
        if self.app_env.lower() == "production":
            if not self.session_cookie_secure:
                raise ValueError("SESSION_COOKIE_SECURE must be true when APP_ENV=production.")
            if "*" in self.cors_origin_list:
                raise ValueError("CORS_ORIGINS must explicitly list frontend origins in production.")
            if self.session_cookie_samesite == "none" and not self.session_cookie_secure:
                raise ValueError("SameSite=None cookies require secure cookies.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
