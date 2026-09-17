from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    service: str
    environment: str
    version: str = "0.1.0"
    checks: dict[str, str] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str | None = None
