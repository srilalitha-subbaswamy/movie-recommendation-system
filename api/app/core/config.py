"""Application configuration using Pydantic Settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    APP_NAME: str = "Movie RecSys API"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    API_V1_PREFIX: str = "/api/v1"

    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "recsys"
    POSTGRES_PASSWORD: str = "changeme"
    POSTGRES_DB: str = "movie_recsys"
    DATABASE_URL: str | None = None

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_TTL_RECOMMENDATIONS: int = 3600
    REDIS_TTL_POPULAR: int = 900
    REDIS_TTL_METADATA: int = 86400

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Models
    ALS_MODEL_PATH: str = "models/als"
    NCF_MODEL_PATH: str = "models/ncf.onnx"

    # TMDB
    TMDB_API_KEY: str = ""

    # Google Auth
    GOOGLE_CLIENT_ID: str = ""
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 72

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100

    @property
    def database_url(self) -> str:
        """Build database URL from components or use explicit URL.

        Handles Render's postgres:// format by converting to postgresql+asyncpg://.
        """
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            # Railway/Render provide postgres:// but asyncpg needs postgresql+asyncpg://
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif not url.startswith("postgresql+asyncpg://"):
                url = f"postgresql+asyncpg://{url.split('://', 1)[-1]}"
            return url
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def database_url_sync(self) -> str:
        """Synchronous database URL for Alembic migrations."""
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            # Normalize to plain postgresql://
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            elif "+asyncpg" in url:
                url = url.replace("+asyncpg", "")
            return url
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
