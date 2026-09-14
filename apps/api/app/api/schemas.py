from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    service: str
    environment: str


class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str | None = None
