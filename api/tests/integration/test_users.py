"""Integration tests for user API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movie import Movie
from app.models.user import User


async def _seed_user(db: AsyncSession, user_id: int = 1, rating_count: int = 10) -> None:
    """Helper to seed a test user."""
    user = User(user_id=user_id, username="testuser", rating_count=rating_count, avg_rating=3.5)
    db.add(user)
    await db.flush()


async def _seed_movie(db: AsyncSession, movie_id: int = 1) -> None:
    """Helper to seed a test movie."""
    movie = Movie(
        movie_id=movie_id,
        title="Test Movie",
        genres=["Drama"],
        year=2024,
        avg_rating=4.0,
        rating_count=100,
    )
    db.add(movie)
    await db.flush()


@pytest.mark.asyncio
class TestUserEndpoints:
    """Tests for user-related endpoints."""

    async def test_get_user(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Get user profile by ID."""
        await _seed_user(db_session)
        await db_session.commit()

        response = await client.get("/api/v1/users/1")
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == 1
        assert data["username"] == "testuser"

    async def test_get_user_not_found(self, client: AsyncClient) -> None:
        """Returns 404 for non-existent user."""
        response = await client.get("/api/v1/users/99999")
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "USER_NOT_FOUND"

    async def test_get_user_ratings_empty(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Get ratings for user with no ratings."""
        await _seed_user(db_session)
        await db_session.commit()

        response = await client.get("/api/v1/users/1/ratings")
        assert response.status_code == 200
        data = response.json()
        assert data["ratings"] == []
        assert data["total"] == 0

    async def test_create_rating(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Create a new rating for a user."""
        await _seed_user(db_session)
        await _seed_movie(db_session)
        await db_session.commit()

        response = await client.post(
            "/api/v1/users/1/ratings",
            json={"movie_id": 1, "rating": 4.5},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == 1
        assert data["movie_id"] == 1
        assert data["rating"] == 4.5

    async def test_create_rating_invalid_value(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Reject rating outside valid range."""
        await _seed_user(db_session)
        await db_session.commit()

        response = await client.post(
            "/api/v1/users/1/ratings",
            json={"movie_id": 1, "rating": 6.0},
        )
        assert response.status_code == 422

    async def test_create_rating_user_not_found(self, client: AsyncClient) -> None:
        """Reject rating for non-existent user."""
        response = await client.post(
            "/api/v1/users/99999/ratings",
            json={"movie_id": 1, "rating": 4.0},
        )
        assert response.status_code == 404
