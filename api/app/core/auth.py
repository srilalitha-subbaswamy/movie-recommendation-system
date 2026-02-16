"""Google OAuth2 + JWT authentication."""

from datetime import datetime, timedelta, timezone

import structlog
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from jose import JWTError, jwt

from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


def verify_google_token(id_token: str) -> dict:
    """Verify a Google ID token and return the user info.

    Returns dict with keys: sub, email, name, picture, email_verified.
    Raises ValueError if token is invalid.
    """
    try:
        idinfo = google_id_token.verify_oauth2_token(
            id_token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
        if idinfo["iss"] not in ("accounts.google.com", "https://accounts.google.com"):
            raise ValueError("Wrong issuer.")
        return idinfo
    except Exception as e:
        logger.warning("google_token_verification_failed", error=str(e))
        raise ValueError(f"Invalid Google token: {e}") from e


def create_access_token(user_id: int, email: str | None = None) -> str:
    """Create a JWT access token."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": now,
        "exp": now + timedelta(hours=settings.JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and verify a JWT access token.

    Returns payload dict with 'sub' (user_id as string), 'email'.
    Raises ValueError if token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}") from e
