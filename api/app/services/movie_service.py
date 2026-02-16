"""Business logic for movie operations."""

import math

import structlog

from app.core.exceptions import MovieNotFoundException
from app.core.redis import cache_get, cache_set
from app.repositories.movie_repository import MovieRepository
from app.schemas.movie import (
    MovieDetail,
    MovieListResponse,
    MovieResponse,
    MovieSearchParams,
)

logger = structlog.get_logger()


class MovieService:
    """Service layer for movie operations."""

    def __init__(self, movie_repo: MovieRepository) -> None:
        self.movie_repo = movie_repo

    async def get_movie(self, movie_id: int) -> MovieDetail:
        """Get a single movie by ID with caching."""
        # Check cache
        cache_key = f"movie:{movie_id}"
        cached = await cache_get(cache_key)
        if cached:
            logger.debug("cache_hit", key=cache_key)
            return MovieDetail(**cached)

        movie = await self.movie_repo.get_by_movie_id(movie_id)
        if not movie:
            raise MovieNotFoundException(movie_id)

        response = MovieDetail.model_validate(movie)

        # Cache for 24 hours
        await cache_set(cache_key, response.model_dump(), ttl=86400)

        return response

    async def search_movies(self, params: MovieSearchParams) -> MovieListResponse:
        """Search movies with filtering, sorting, and pagination."""
        movies, total = await self.movie_repo.search(params)

        total_pages = math.ceil(total / params.page_size) if total > 0 else 0

        return MovieListResponse(
            movies=[MovieResponse.model_validate(m) for m in movies],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    async def get_popular_movies(
        self, limit: int = 20, genre: str | None = None
    ) -> list[MovieResponse]:
        """Get popular movies with caching."""
        cache_key = f"popular:{genre or 'all'}"
        cached = await cache_get(cache_key)
        if cached:
            return [MovieResponse(**m) for m in cached]

        movies = await self.movie_repo.get_popular(limit=limit, genre=genre)
        response = [MovieResponse.model_validate(m) for m in movies]

        # Cache for 15 minutes
        await cache_set(cache_key, [r.model_dump() for r in response], ttl=900)

        return response
