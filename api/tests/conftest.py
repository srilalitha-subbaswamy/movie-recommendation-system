"""Shared test fixtures for the API test suite."""

import asyncio
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean in-memory database session for each test.

    Uses in-memory SQLite with a shared connection and StaticPool
    to ensure all operations share the same database state.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide a test HTTP client with overridden database dependency.

    Uses a separate app instance without lifespan to avoid
    connecting to real PostgreSQL/Redis during tests.
    """
    from contextlib import asynccontextmanager
    from collections.abc import AsyncIterator

    from fastapi import FastAPI

    @asynccontextmanager
    async def test_lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield

    # Create test app with no-op lifespan
    from app.core.config import get_settings
    from app.core.exceptions import AppException
    from app.routers import health, movies, recommendations, users
    from fastapi.responses import JSONResponse
    from fastapi import Request

    settings = get_settings()

    test_app = FastAPI(lifespan=test_lifespan)
    test_app.include_router(health.router, prefix=settings.API_V1_PREFIX)
    test_app.include_router(movies.router, prefix=settings.API_V1_PREFIX)
    test_app.include_router(recommendations.router, prefix=settings.API_V1_PREFIX)
    test_app.include_router(users.router, prefix=settings.API_V1_PREFIX)

    @test_app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.error_code, "message": exc.message},
        )

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    test_app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as ac:
        yield ac

    test_app.dependency_overrides.clear()
