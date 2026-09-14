from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TrustID API"
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://trustid:trustid@localhost:5432/trustid"
    redis_url: str = "redis://localhost:6379/0"
    object_storage_endpoint: str = "http://localhost:9000"
    object_storage_bucket: str = "trustid-documents"
    object_storage_access_key: str = "minioadmin"
    object_storage_secret_key: str = "minioadmin"
    ocr_provider: str = "demo"
    cors_origins: str = "http://localhost:3000"
    demo_password: str | None = None
    session_cookie_name: str = "trustid_session"
    session_cookie_secure: bool = False
    session_cookie_max_age: int = 28800

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
