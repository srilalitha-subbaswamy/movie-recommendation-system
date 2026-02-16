"""Health check endpoints for liveness and readiness probes."""

import time

import structlog
from fastapi import APIRouter
from sqlalchemy import text

from app.core.database import async_session_factory
from app.core.redis import get_redis
from app.schemas.health import HealthResponse, ReadinessCheck, ReadinessResponse

router = APIRouter(tags=["health"])
logger = structlog.get_logger()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Liveness probe - returns OK if the service is running."""
    return HealthResponse(status="ok", version="1.0.0")


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check() -> ReadinessResponse:
    """Readiness probe - checks all dependencies."""
    db_check = await _check_database()
    redis_check = await _check_redis()
    models_check = _check_models()

    all_healthy = all(
        c.status == "ok" for c in [db_check, redis_check, models_check]
    )

    return ReadinessResponse(
        status="ok" if all_healthy else "degraded",
        database=db_check,
        redis=redis_check,
        models=models_check,
    )


async def _check_database() -> ReadinessCheck:
    """Check database connectivity."""
    start = time.monotonic()
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        latency = (time.monotonic() - start) * 1000
        return ReadinessCheck(status="ok", latency_ms=round(latency, 2))
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        logger.error("database_health_check_failed", error=str(e))
        return ReadinessCheck(
            status="error", latency_ms=round(latency, 2), error=str(e)
        )


async def _check_redis() -> ReadinessCheck:
    """Check Redis connectivity."""
    start = time.monotonic()
    try:
        client = get_redis()
        if client is None:
            return ReadinessCheck(status="error", error="Redis not initialized")
        await client.ping()
        latency = (time.monotonic() - start) * 1000
        return ReadinessCheck(status="ok", latency_ms=round(latency, 2))
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        logger.error("redis_health_check_failed", error=str(e))
        return ReadinessCheck(
            status="error", latency_ms=round(latency, 2), error=str(e)
        )


def _check_models() -> ReadinessCheck:
    """Check if ML models are loaded.

    For MVP, this always returns OK since we use database-backed
    recommendations. In production, this would verify ONNX/ALS
    model files are loaded in memory.
    """
    return ReadinessCheck(status="ok", latency_ms=0)
