"""Integration tests for movie API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movie import Movie


async def _seed_movies(db: AsyncSession) -> None:
    """Helper to seed test movies."""
    movies = [
        Movie(
            movie_id=1,
            title="Toy Story",
            genres=["Animation", "Comedy"],
            year=1995,
            avg_rating=3.89,
            rating_count=73215,
        ),
        Movie(
            movie_id=2,
            title="Jumanji",
            genres=["Adventure", "Fantasy"],
            year=1995,
            avg_rating=3.21,
            rating_count=31078,
        ),
        Movie(
            movie_id=296,
            title="Pulp Fiction",
            genres=["Crime", "Drama", "Thriller"],
            year=1994,
            avg_rating=4.20,
            rating_count=92406,
        ),
        Movie(
            movie_id=318,
            title="The Shawshank Redemption",
            genres=["Crime", "Drama"],
            year=1994,
            avg_rating=4.43,
            rating_count=97999,
        ),
        Movie(
            movie_id=2571,
            title="The Matrix",
            genres=["Action", "Sci-Fi", "Thriller"],
            year=1999,
            avg_rating=4.19,
            rating_count=84545,
        ),
    ]
    for m in movies:
        db.add(m)
    await db.flush()


@pytest.mark.asyncio
class TestMovieEndpoints:
    """Tests for movie CRUD and search endpoints."""

    async def test_search_movies_empty(self, client: AsyncClient) -> None:
        """Search with no data returns empty list."""
        response = await client.get("/api/v1/movies")
        assert response.status_code == 200
        data = response.json()
        assert data["movies"] == []
        assert data["total"] == 0

    async def test_search_movies_with_data(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Search returns movies when data exists."""
        await _seed_movies(db_session)
        await db_session.commit()

        response = await client.get("/api/v1/movies")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["movies"]) == 5

    async def test_search_by_title(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Search filters by title correctly."""
        await _seed_movies(db_session)
        await db_session.commit()

        response = await client.get("/api/v1/movies", params={"query": "Matrix"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["movies"][0]["title"] == "The Matrix"

    async def test_search_by_genre(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Search filters by genre correctly."""
        await _seed_movies(db_session)
        await db_session.commit()

        response = await client.get("/api/v1/movies", params={"genre": "Animation"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert "Animation" in data["movies"][0]["genres"]

    async def test_search_pagination(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Pagination works correctly."""
        await _seed_movies(db_session)
        await db_session.commit()

        response = await client.get(
            "/api/v1/movies", params={"page": 1, "page_size": 2}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["movies"]) == 2
        assert data["total"] == 5
        assert data["total_pages"] == 3

    async def test_get_movie_by_id(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Get specific movie by ID."""
        await _seed_movies(db_session)
        await db_session.commit()

        response = await client.get("/api/v1/movies/318")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "The Shawshank Redemption"
        assert data["movie_id"] == 318

    async def test_get_movie_not_found(self, client: AsyncClient) -> None:
        """Returns 404 for non-existent movie."""
        response = await client.get("/api/v1/movies/99999")
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "MOVIE_NOT_FOUND"

    async def test_get_popular_movies(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Get popular movies sorted by rating count."""
        await _seed_movies(db_session)
        await db_session.commit()

        response = await client.get("/api/v1/movies/popular", params={"limit": 3})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        # Should be sorted by rating_count descending
        assert data[0]["rating_count"] >= data[1]["rating_count"]
