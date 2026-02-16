"""Google OAuth2 authentication endpoints."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_access_token, decode_access_token, verify_google_token
from app.core.config import get_settings
from app.core.database import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])
logger = structlog.get_logger()
settings = get_settings()


class GoogleLoginRequest(BaseModel):
    """Request body for Google login."""

    id_token: str


class AuthResponse(BaseModel):
    """Response with user profile and access token."""

    user: UserResponse
    access_token: str


@router.post("/google", response_model=AuthResponse)
async def google_login(
    body: GoogleLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Authenticate with Google ID token.

    - Verifies the Google token
    - Finds or creates a user record
    - Returns a JWT access token
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google Sign-In not configured")

    try:
        google_info = verify_google_token(body.id_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e

    google_id = google_info["sub"]
    email = google_info.get("email", "")
    name = google_info.get("name", email.split("@")[0])
    picture = google_info.get("picture")

    repo = UserRepository(db)

    # Find existing user by Google ID
    user = await repo.get_by_google_id(google_id)

    if not user:
        # Create new user
        new_user_id = await repo.get_next_user_id()
        user = await repo.create_google_user(
            user_id=new_user_id,
            google_id=google_id,
            email=email,
            username=name,
            avatar_url=picture,
        )
        logger.info("google_user_created", user_id=new_user_id, email=email)
    else:
        # Update profile info if changed
        if user.username != name or user.avatar_url != picture:
            user.username = name
            user.avatar_url = picture
            await db.flush()

    await db.commit()

    token = create_access_token(user.user_id, email=email)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=token,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Get the currently authenticated user's profile."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = auth_header.split(" ", 1)[1]

    try:
        payload = decode_access_token(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e

    user_id = int(payload["sub"])
    repo = UserRepository(db)
    user = await repo.get_by_user_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse.model_validate(user)
