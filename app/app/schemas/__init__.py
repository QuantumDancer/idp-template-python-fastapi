from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class ReadinessResponse(BaseModel):
    status: str
    # Keyed by dependency name; value is "ok" or a human-readable error message
    checks: dict[str, str] = {}
