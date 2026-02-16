"""Unit tests for application configuration."""

from app.core.config import Settings


class TestSettings:
    """Tests for Pydantic settings."""

    def test_default_values(self) -> None:
        settings = Settings(
            POSTGRES_HOST="localhost",
            POSTGRES_USER="recsys",
            POSTGRES_PASSWORD="secret",
            POSTGRES_DB="testdb",
        )
        assert settings.APP_NAME == "Movie RecSys API"
        assert settings.DEBUG is False
        assert settings.POSTGRES_PORT == 5432
        assert settings.REDIS_TTL_RECOMMENDATIONS == 3600

    def test_database_url_constructed(self) -> None:
        settings = Settings(
            POSTGRES_HOST="myhost",
            POSTGRES_PORT=5433,
            POSTGRES_USER="user",
            POSTGRES_PASSWORD="pass",
            POSTGRES_DB="db",
        )
        assert settings.database_url == "postgresql+asyncpg://user:pass@myhost:5433/db"

    def test_database_url_explicit(self) -> None:
        settings = Settings(
            POSTGRES_HOST="localhost",
            POSTGRES_USER="recsys",
            POSTGRES_PASSWORD="secret",
            POSTGRES_DB="testdb",
            DATABASE_URL="postgresql+asyncpg://custom:url@host/db",
        )
        assert settings.database_url == "postgresql+asyncpg://custom:url@host/db"

    def test_database_url_sync(self) -> None:
        settings = Settings(
            POSTGRES_HOST="localhost",
            POSTGRES_USER="recsys",
            POSTGRES_PASSWORD="secret",
            POSTGRES_DB="testdb",
        )
        sync_url = settings.database_url_sync
        assert "+asyncpg" not in sync_url
        assert "postgresql://" in sync_url

    def test_cors_origins_default(self) -> None:
        settings = Settings(
            POSTGRES_HOST="localhost",
            POSTGRES_USER="recsys",
            POSTGRES_PASSWORD="secret",
            POSTGRES_DB="testdb",
        )
        assert "http://localhost:5173" in settings.CORS_ORIGINS
        assert "http://localhost:3000" in settings.CORS_ORIGINS
