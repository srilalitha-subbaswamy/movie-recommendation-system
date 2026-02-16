"""Pydantic schemas for health check endpoints."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Liveness probe response."""

    status: str = "ok"
    version: str = "1.0.0"


class ReadinessCheck(BaseModel):
    """Individual service check result."""

    status: str
    latency_ms: float | None = None
    error: str | None = None


class ReadinessResponse(BaseModel):
    """Readiness probe response with dependency checks."""

    status: str
    database: ReadinessCheck
    redis: ReadinessCheck
    models: ReadinessCheck
