"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import get_settings
from app.core.database import close_db, init_db
from app.core.exceptions import AppException
from app.core.logging import setup_logging
from app.core.embedding_index import build_embedding_index
from app.core.model_loader import load_als_model
from app.core.redis import close_redis, init_redis
from app.routers import auth, discover, health, movies, recommendations, users

settings = get_settings()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup and shutdown lifecycle."""
    # Startup
    setup_logging(json_logs=not settings.DEBUG, log_level=settings.LOG_LEVEL)
    logger.info("application_starting", app=settings.APP_NAME, debug=settings.DEBUG)

    try:
        await init_db()
        logger.info("database_connected")
    except Exception as e:
        logger.error("database_connection_failed", error=str(e))

    await init_redis()

    # Load ALS model
    load_als_model(settings.ALS_MODEL_PATH)

    # Build embedding index for semantic search
    try:
        await build_embedding_index(data_dir="data/raw/ml-latest-small")
    except Exception as e:
        logger.error("embedding_index_failed", error=str(e))

    logger.info("application_started")
    yield

    # Shutdown
    await close_redis()
    await close_db()
    logger.info("application_shutdown")


app = FastAPI(
    title="Movie Recommendation API",
    description="Production-grade movie recommendation system with ALS + Neural CF",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# Routers
app.include_router(health.router, prefix=settings.API_V1_PREFIX)
app.include_router(movies.router, prefix=settings.API_V1_PREFIX)
app.include_router(recommendations.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
app.include_router(discover.router, prefix=settings.API_V1_PREFIX)
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle custom application exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.error_code, "message": exc.message},
    )
