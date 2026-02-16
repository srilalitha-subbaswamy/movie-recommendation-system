"""Data access layer for movies."""

from sqlalchemy import Select, cast, func, select, String
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movie import Movie
from app.schemas.movie import MovieSearchParams


class MovieRepository:
    """Repository for movie database operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_movie_id(self, movie_id: int) -> Movie | None:
        """Get a movie by its movie_id."""
        result = await self.db.execute(
            select(Movie).where(Movie.movie_id == movie_id)
        )
        return result.scalar_one_or_none()

    async def get_by_movie_ids(self, movie_ids: list[int]) -> list[Movie]:
        """Get multiple movies by their movie_ids."""
        result = await self.db.execute(
            select(Movie).where(Movie.movie_id.in_(movie_ids))
        )
        return list(result.scalars().all())

    async def search(self, params: MovieSearchParams) -> tuple[list[Movie], int]:
        """Search movies with filtering, sorting, and pagination.

        Returns:
            Tuple of (movies, total_count).
        """
        query = select(Movie)
        count_query = select(func.count()).select_from(Movie)

        # Apply filters
        query, count_query = self._apply_filters(query, count_query, params)

        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply sorting
        query = self._apply_sorting(query, params.sort_by)

        # Apply pagination
        offset = (params.page - 1) * params.page_size
        query = query.offset(offset).limit(params.page_size)

        result = await self.db.execute(query)
        movies = list(result.scalars().all())

        return movies, total

    async def get_popular(self, limit: int = 20, genre: str | None = None) -> list[Movie]:
        """Get popular movies, optionally filtered by genre."""
        query = (
            select(Movie)
            .where(Movie.rating_count > 0)
            .order_by(Movie.rating_count.desc())
        )
        if genre:
            query = query.where(cast(Movie.genres, String).contains(genre))
        query = query.limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_top_rated(self, limit: int = 20, min_ratings: int = 10) -> list[Movie]:
        """Get top-rated movies with a minimum number of ratings."""
        query = (
            select(Movie)
            .where(Movie.rating_count >= min_ratings)
            .order_by(Movie.avg_rating.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_all_movie_ids(self) -> set[int]:
        """Get all movie IDs in the database."""
        result = await self.db.execute(select(Movie.movie_id))
        return set(result.scalars().all())

    async def count(self) -> int:
        """Get total movie count."""
        result = await self.db.execute(select(func.count()).select_from(Movie))
        return result.scalar() or 0

    def _apply_filters(
        self,
        query: Select[tuple[Movie]],
        count_query: Select[tuple[int]],
        params: MovieSearchParams,
    ) -> tuple[Select[tuple[Movie]], Select[tuple[int]]]:
        """Apply search filters to both data and count queries."""
        if params.query:
            filter_expr = Movie.title.ilike(f"%{params.query}%")
            query = query.where(filter_expr)
            count_query = count_query.where(filter_expr)

        if params.genre:
            genre_filter = cast(Movie.genres, String).contains(params.genre)
            query = query.where(genre_filter)
            count_query = count_query.where(genre_filter)

        if params.year_min:
            query = query.where(Movie.year >= params.year_min)
            count_query = count_query.where(Movie.year >= params.year_min)

        if params.year_max:
            query = query.where(Movie.year <= params.year_max)
            count_query = count_query.where(Movie.year <= params.year_max)

        if params.min_rating:
            query = query.where(Movie.avg_rating >= params.min_rating)
            count_query = count_query.where(Movie.avg_rating >= params.min_rating)

        return query, count_query

    def _apply_sorting(
        self, query: Select[tuple[Movie]], sort_by: str
    ) -> Select[tuple[Movie]]:
        """Apply sorting to query."""
        sort_map = {
            "popularity": Movie.rating_count.desc(),
            "rating": Movie.avg_rating.desc(),
            "year": Movie.year.desc().nulls_last(),
            "title": Movie.title.asc(),
        }
        order = sort_map.get(sort_by, Movie.rating_count.desc())
        return query.order_by(order)
