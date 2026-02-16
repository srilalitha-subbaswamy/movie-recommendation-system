"""Data access layer for ratings."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rating import Rating


class RatingRepository:
    """Repository for rating database operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_user_ratings(
        self, user_id: int, page: int = 1, page_size: int = 20
    ) -> tuple[list[Rating], int]:
        """Get paginated ratings for a user.

        Returns:
            Tuple of (ratings, total_count).
        """
        # Total count
        count_result = await self.db.execute(
            select(func.count()).select_from(Rating).where(Rating.user_id == user_id)
        )
        total = count_result.scalar() or 0

        # Paginated results
        offset = (page - 1) * page_size
        result = await self.db.execute(
            select(Rating)
            .where(Rating.user_id == user_id)
            .order_by(Rating.timestamp.desc())
            .offset(offset)
            .limit(page_size)
        )
        ratings = list(result.scalars().all())

        return ratings, total

    async def get_user_ratings_with_movies(
        self, user_id: int, page: int = 1, page_size: int = 20
    ) -> tuple[list[dict], int]:
        """Get paginated ratings with movie metadata for a user."""
        from sqlalchemy import text

        # Total count
        count_result = await self.db.execute(
            select(func.count()).select_from(Rating).where(Rating.user_id == user_id)
        )
        total = count_result.scalar() or 0

        offset = (page - 1) * page_size
        result = await self.db.execute(
            text("""
                SELECT r.user_id, r.movie_id, r.rating, r.timestamp,
                       m.title, m.genres, m.year, m.poster_url, m.avg_rating
                FROM ratings r
                JOIN movies m ON r.movie_id = m.movie_id
                WHERE r.user_id = :user_id
                ORDER BY r.timestamp DESC
                OFFSET :offset LIMIT :limit
            """),
            {"user_id": user_id, "offset": offset, "limit": page_size},
        )
        rows = result.fetchall()

        import json
        ratings_with_movies = []
        for row in rows:
            genres_raw = row[5]
            if isinstance(genres_raw, str):
                genres = json.loads(genres_raw)
            elif isinstance(genres_raw, list):
                genres = genres_raw
            else:
                genres = None

            ratings_with_movies.append({
                "user_id": row[0],
                "movie_id": row[1],
                "rating": row[2],
                "timestamp": row[3],
                "movie_title": row[4],
                "movie_genres": genres,
                "movie_year": row[6],
                "movie_poster_url": row[7],
                "movie_avg_rating": row[8],
            })

        return ratings_with_movies, total

    async def create(self, user_id: int, movie_id: int, rating: float) -> Rating:
        """Create or update a rating."""
        from datetime import datetime, timezone

        # Check for existing rating
        result = await self.db.execute(
            select(Rating).where(
                Rating.user_id == user_id,
                Rating.movie_id == movie_id,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.rating = rating
            existing.timestamp = datetime.utcnow()
            await self.db.flush()
            return existing

        new_rating = Rating(user_id=user_id, movie_id=movie_id, rating=rating)
        self.db.add(new_rating)
        await self.db.flush()
        return new_rating

    async def get_user_rated_movie_ids(self, user_id: int) -> set[int]:
        """Get the set of movie IDs the user has rated."""
        result = await self.db.execute(
            select(Rating.movie_id).where(Rating.user_id == user_id)
        )
        return set(result.scalars().all())

    async def get_user_rating_for_movie(self, user_id: int, movie_id: int) -> Rating | None:
        """Get a user's rating for a specific movie."""
        result = await self.db.execute(
            select(Rating).where(
                Rating.user_id == user_id,
                Rating.movie_id == movie_id,
            )
        )
        return result.scalar_one_or_none()

    async def delete(self, user_id: int, movie_id: int) -> bool:
        """Delete a rating. Returns True if deleted, False if not found."""
        result = await self.db.execute(
            select(Rating).where(
                Rating.user_id == user_id,
                Rating.movie_id == movie_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            await self.db.delete(existing)
            await self.db.flush()
            return True
        return False

    async def get_user_rating_stats(self, user_id: int) -> dict:
        """Get aggregate rating statistics for a user.

        Returns dict with total_rated, avg_rating, rating_distribution, genre_breakdown.
        """
        from sqlalchemy import text

        # Basic stats
        count_result = await self.db.execute(
            select(func.count(), func.avg(Rating.rating))
            .where(Rating.user_id == user_id)
        )
        row = count_result.one()
        total_rated = row[0] or 0
        avg_rating = round(float(row[1] or 0), 2)

        # Rating distribution
        dist_result = await self.db.execute(
            select(Rating.rating, func.count())
            .where(Rating.user_id == user_id)
            .group_by(Rating.rating)
            .order_by(Rating.rating)
        )
        rating_distribution = {str(r[0]): r[1] for r in dist_result.fetchall()}

        # Genre breakdown (join ratings with movies)
        # Use json_array_elements_text to unnest the JSON array and group properly
        genre_result = await self.db.execute(
            text("""
                SELECT g.genre, COUNT(*) as cnt
                FROM ratings r
                JOIN movies m ON r.movie_id = m.movie_id
                CROSS JOIN LATERAL json_array_elements_text(m.genres) AS g(genre)
                WHERE r.user_id = :user_id AND m.genres IS NOT NULL
                GROUP BY g.genre
                ORDER BY cnt DESC
            """),
            {"user_id": user_id},
        )
        genre_counts: dict[str, int] = {}
        for row_data in genre_result.fetchall():
            genre, cnt = row_data[0], row_data[1]
            genre_counts[genre] = cnt

        # Sort by count descending
        genre_breakdown = dict(sorted(genre_counts.items(), key=lambda x: -x[1]))

        return {
            "total_rated": total_rated,
            "avg_rating": avg_rating,
            "rating_distribution": rating_distribution,
            "genre_breakdown": genre_breakdown,
        }

    async def get_user_rating_count(self, user_id: int) -> int:
        """Get total number of ratings for a user."""
        result = await self.db.execute(
            select(func.count()).select_from(Rating).where(Rating.user_id == user_id)
        )
        return result.scalar() or 0
