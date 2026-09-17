from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

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
    external_verification_provider: str = "production"
    external_verification_timeout_seconds: float = 10.0
    analysis_processing_timeout_seconds: float = 1800.0
    face_model_path: str = "models/face_recognition_sface_2021dec.onnx"
    face_model_sha256: str | None = None
    face_detector: str = "haar"
    face_detector_model_path: str = "models/face_detection_yunet_2023mar.onnx"
    face_detector_model_sha256: str | None = None
    face_detector_score_threshold: float = 0.9
    face_box_padding: float = 0.0
    face_min_face_pixels: int = 6400
    face_blur_threshold: float = 20.0
    face_brightness_min: float = 35.0
    face_brightness_max: float = 225.0
    face_contrast_min: float = 18.0
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
        if self.ocr_provider.lower() not in {"demo", "production"}:
            raise ValueError("OCR_PROVIDER must be either demo or production.")
        if self.face_provider.lower() not in {"demo", "production"}:
            raise ValueError("FACE_VERIFICATION_PROVIDER must be either demo or production.")
        if self.external_verification_provider.lower() not in {"demo", "production"}:
            raise ValueError("EXTERNAL_VERIFICATION_PROVIDER must be either demo or production.")
        if not 1 <= self.external_verification_timeout_seconds <= 60:
            raise ValueError("EXTERNAL_VERIFICATION_TIMEOUT_SECONDS must be between 1 and 60.")
        if not 60 <= self.analysis_processing_timeout_seconds <= 86400:
            raise ValueError("ANALYSIS_PROCESSING_TIMEOUT_SECONDS must be between 60 and 86400.")
        if self.app_env.lower() == "production":
            required = {
                "DATABASE_URL": self.database_url,
                "REDIS_URL": self.redis_url,
                "OBJECT_STORAGE_ENDPOINT": self.object_storage_endpoint,
                "OBJECT_STORAGE_REGION": self.object_storage_region,
                "OBJECT_STORAGE_BUCKET": self.object_storage_bucket,
                "OBJECT_STORAGE_ACCESS_KEY": self.object_storage_access_key,
                "OBJECT_STORAGE_SECRET_KEY": self.object_storage_secret_key,
                "DEMO_PASSWORD": self.demo_password or "",
            }
            missing = [name for name, value in required.items() if not value.strip()]
            if missing:
                raise ValueError(f"Required production settings are missing: {', '.join(missing)}.")
            localhost_values = {
                "DATABASE_URL": self.database_url,
                "REDIS_URL": self.redis_url,
                "OBJECT_STORAGE_ENDPOINT": self.object_storage_endpoint,
            }
            localhost_names = [
                name
                for name, value in localhost_values.items()
                if urlparse(value).hostname in {"localhost", "127.0.0.1", "::1"}
            ]
            if localhost_names:
                raise ValueError(f"Production settings must not use localhost: {', '.join(localhost_names)}.")
            endpoint = urlparse(self.object_storage_endpoint)
            if endpoint.scheme not in {"http", "https"} or not endpoint.hostname:
                raise ValueError("OBJECT_STORAGE_ENDPOINT must be a valid HTTP(S) URL in production.")
            if any(value.startswith("replace-with-") for value in (self.object_storage_access_key, self.object_storage_secret_key)):
                raise ValueError("Production object storage credentials must be configured.")
            if self.object_storage_access_key == "minioadmin" or self.object_storage_secret_key == "minioadmin":
                raise ValueError("Production object storage credentials must not use local MinIO defaults.")
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
