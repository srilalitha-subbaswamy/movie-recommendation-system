"""Integration tests for recommendation API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movie import Movie
from app.models.user import User


async def _seed_data(db: AsyncSession) -> None:
    """Seed movies and users for recommendation tests."""
    movies = [
        Movie(movie_id=1, title="Toy Story", genres=["Animation"], year=1995, avg_rating=3.89, rating_count=73215),
        Movie(movie_id=2, title="Jumanji", genres=["Adventure"], year=1995, avg_rating=3.21, rating_count=31078),
        Movie(movie_id=318, title="Shawshank", genres=["Drama"], year=1994, avg_rating=4.43, rating_count=97999),
    ]
    users = [
        User(user_id=1, username="active", rating_count=50, avg_rating=3.5),
        User(user_id=2, username="new", rating_count=0, avg_rating=0.0),
        User(user_id=3, username="few", rating_count=3, avg_rating=4.0),
    ]
    for m in movies:
        db.add(m)
    for u in users:
        db.add(u)
    await db.flush()


@pytest.mark.asyncio
class TestRecommendationEndpoints:
    """Tests for recommendation endpoints."""

    async def test_get_recommendations_active_user(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Active user gets collaborative recommendations."""
        await _seed_data(db_session)
        await db_session.commit()

        response = await client.get("/api/v1/recommendations/1")
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == 1
        assert data["strategy"] == "collaborative"
        assert len(data["recommendations"]) > 0
        assert "latency_ms" in data

    async def test_get_recommendations_new_user(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """New user with 0 ratings gets popular recommendations."""
        await _seed_data(db_session)
        await db_session.commit()

        response = await client.get("/api/v1/recommendations/2")
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == 2
        assert data["strategy"] == "popular"

    async def test_get_recommendations_few_ratings(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """User with few ratings gets content-based fallback."""
        await _seed_data(db_session)
        await db_session.commit()

        response = await client.get("/api/v1/recommendations/3")
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == 3
        assert data["strategy"] == "content_based"

    async def test_get_recommendations_user_not_found(
        self, client: AsyncClient
    ) -> None:
        """Returns 404 for non-existent user."""
        response = await client.get("/api/v1/recommendations/99999")
        assert response.status_code == 404

    async def test_get_recommendations_with_limit(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Limit parameter controls number of results."""
        await _seed_data(db_session)
        await db_session.commit()

        response = await client.get(
            "/api/v1/recommendations/1", params={"limit": 2}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["recommendations"]) <= 2

    async def test_get_similar_movies(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Get movies similar to a given movie."""
        await _seed_data(db_session)
        await db_session.commit()

        response = await client.get("/api/v1/recommendations/similar/1")
        assert response.status_code == 200
        data = response.json()
        assert data["movie_id"] == 1
        assert "similar_movies" in data
        assert "latency_ms" in data

    async def test_get_similar_movie_not_found(self, client: AsyncClient) -> None:
        """Returns 404 for non-existent movie."""
        response = await client.get("/api/v1/recommendations/similar/99999")
        assert response.status_code == 404

    async def test_recommendation_response_has_explanations(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Each recommendation includes an explanation."""
        await _seed_data(db_session)
        await db_session.commit()

        response = await client.get("/api/v1/recommendations/1?explain=true")
        assert response.status_code == 200
        data = response.json()
        for rec in data["recommendations"]:
            assert "explanation" in rec
            assert len(rec["explanation"]) > 0
