"""
models/schemas.py
Pydantic response schemas for FastAPI automatic OpenAPI documentation.
"""

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from config.constants import API_VERSION


class HealthResponse(BaseModel):
    status: str = Field(..., json_schema_extra={"example": "healthy"})
    engine: str = Field(..., json_schema_extra={"example": "rembg-silueta"})
    model_loaded: bool = Field(..., json_schema_extra={"example": True})
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        json_schema_extra={"example": "2025-01-01T00:00:00+00:00"}
    )


class RootResponse(BaseModel):
    name: str = "Background Remover API"
    version: str = API_VERSION
    status: str = "running"


class ErrorResponse(BaseModel):
    detail: str = Field(..., json_schema_extra={"example": "Unsupported image format."})
