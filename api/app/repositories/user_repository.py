"""Data access layer for users."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    """Repository for user database operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_user_id(self, user_id: int) -> User | None:
        """Get a user by their user_id."""
        result = await self.db.execute(
            select(User).where(User.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_google_id(self, google_id: str) -> User | None:
        """Get a user by their Google ID."""
        result = await self.db.execute(
            select(User).where(User.google_id == google_id)
        )
        return result.scalar_one_or_none()

    async def get_next_user_id(self) -> int:
        """Get the next available user_id for new users."""
        from sqlalchemy import func

        result = await self.db.execute(select(func.max(User.user_id)))
        max_id = result.scalar() or 0
        return max(max_id + 1, 10000)  # Google users start from 10000+

    async def create(self, user_id: int, username: str | None = None) -> User:
        """Create a new user."""
        user = User(user_id=user_id, username=username)
        self.db.add(user)
        await self.db.flush()
        return user

    async def create_google_user(
        self,
        user_id: int,
        google_id: str,
        email: str,
        username: str | None = None,
        avatar_url: str | None = None,
    ) -> User:
        """Create a new user from Google Sign-In."""
        user = User(
            user_id=user_id,
            google_id=google_id,
            email=email,
            username=username,
            avatar_url=avatar_url,
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def update_stats(self, user_id: int, rating_count: int, avg_rating: float) -> None:
        """Update user rating statistics."""
        result = await self.db.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.rating_count = rating_count
            user.avg_rating = avg_rating
            await self.db.flush()
