"""Business logic for generating recommendations.

Implements a tiered strategy using ALS collaborative filtering:
- Cold start (0 ratings): popular movies
- Warm start (<5 ratings): content-based fallback via genre similarity
- Full personalization (5+ ratings): ALS dot-product scoring
"""

import time
from datetime import datetime, timezone

import structlog

from app.core.config import get_settings
from app.core.exceptions import UserNotFoundException
from app.core.model_loader import get_als_model
from app.core.redis import cache_get, cache_set
from app.repositories.movie_repository import MovieRepository
from app.repositories.rating_repository import RatingRepository
from app.repositories.user_repository import UserRepository
from app.schemas.recommendation import (
    RecommendationItem,
    RecommendationResponse,
    SimilarMoviesResponse,
)

logger = structlog.get_logger()
settings = get_settings()


class RecommendationService:
    """Service for generating personalized movie recommendations.

    Implements a tiered strategy:
    - Cold start (0 ratings): popular movies
    - Warm start (<5 ratings): content-based fallback
    - Full collaborative filtering (5+ ratings): ALS model inference
    """

    def __init__(
        self,
        user_repo: UserRepository,
        movie_repo: MovieRepository,
        rating_repo: RatingRepository,
    ) -> None:
        self.user_repo = user_repo
        self.movie_repo = movie_repo
        self.rating_repo = rating_repo

    async def get_recommendations(
        self,
        user_id: int,
        limit: int = 20,
        explain: bool = False,
    ) -> RecommendationResponse:
        """Get personalized recommendations with cold start fallback."""
        start_time = time.monotonic()

        # Check cache first
        cache_key = f"recs:{user_id}:{limit}"
        cached = await cache_get(cache_key)
        if cached:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            logger.info(
                "recommendation_served",
                user_id=user_id,
                cached=True,
                latency_ms=round(elapsed_ms, 2),
            )
            response = RecommendationResponse(**cached)
            response.cached = True
            response.latency_ms = round(elapsed_ms, 2)
            return response

        user = await self.user_repo.get_by_user_id(user_id)
        if user is None:
            raise UserNotFoundException(user_id)

        # Tiered recommendation strategy
        if user.rating_count == 0:
            response = await self._get_onboarding_recommendations(user_id, limit)
        elif user.rating_count < 5:
            response = await self._get_content_based_fallback(user_id, limit)
        else:
            response = await self._get_collaborative_recommendations(user_id, limit)

        elapsed_ms = (time.monotonic() - start_time) * 1000
        response.latency_ms = round(elapsed_ms, 2)

        # Cache recommendations
        await cache_set(
            cache_key,
            response.model_dump(),
            ttl=settings.REDIS_TTL_RECOMMENDATIONS,
        )

        logger.info(
            "recommendation_generated",
            user_id=user_id,
            strategy=response.strategy,
            count=len(response.recommendations),
            latency_ms=response.latency_ms,
        )

        return response

    async def get_similar_movies(
        self, movie_id: int, limit: int = 10
    ) -> SimilarMoviesResponse:
        """Get movies similar to a given movie using ALS item factors."""
        start_time = time.monotonic()

        source_movie = await self.movie_repo.get_by_movie_id(movie_id)
        if not source_movie:
            from app.core.exceptions import MovieNotFoundException

            raise MovieNotFoundException(movie_id)

        model = get_als_model()

        if model.is_loaded and model.has_item(movie_id):
            # Use ALS item-factor cosine similarity, constrained to DB movies
            db_movie_ids = await self.movie_repo.get_all_movie_ids()
            similar_pairs = model.get_similar_items(
                movie_id, top_k=limit, candidate_ids=db_movie_ids
            )
            similar_movie_ids = [mid for mid, _ in similar_pairs]
            score_map = dict(similar_pairs)

            # Fetch movie metadata from DB
            movies = await self.movie_repo.get_by_movie_ids(similar_movie_ids)
            movie_map = {m.movie_id: m for m in movies}

            items = []
            for mid in similar_movie_ids:
                m = movie_map.get(mid)
                if m is None:
                    continue
                sim_score = score_map.get(mid, 0.0)
                items.append(
                    RecommendationItem(
                        movie_id=m.movie_id,
                        title=m.title,
                        genres=m.genres,
                        year=m.year,
                        poster_url=m.poster_url,
                        avg_rating=m.avg_rating,
                        rating_count=m.rating_count,
                        predicted_rating=round(sim_score * 5, 2),
                        explanation=f"Cosine similarity: {sim_score:.2f}",
                        confidence=round(min(abs(sim_score), 1.0), 2),
                        model_source="als",
                    )
                )
                if len(items) >= limit:
                    break
        else:
            # Fallback: popular movies in same genre
            genre = source_movie.genres[0] if source_movie.genres else None
            similar = await self.movie_repo.get_popular(limit=limit + 1, genre=genre)
            similar = [m for m in similar if m.movie_id != movie_id][:limit]

            items = [
                RecommendationItem(
                    movie_id=m.movie_id,
                    title=m.title,
                    genres=m.genres,
                    year=m.year,
                    poster_url=m.poster_url,
                    avg_rating=m.avg_rating,
                    rating_count=m.rating_count,
                    predicted_rating=m.avg_rating,
                    explanation=f"Similar genre: {genre}" if genre else "Popular movie",
                    confidence=0.5,
                    model_source="popular",
                )
                for m in similar
            ]

        elapsed_ms = (time.monotonic() - start_time) * 1000
        return SimilarMoviesResponse(
            movie_id=movie_id,
            title=source_movie.title,
            similar_movies=items,
            generated_at=datetime.now(timezone.utc),
            latency_ms=round(elapsed_ms, 2),
        )

    async def _get_onboarding_recommendations(
        self, user_id: int, limit: int
    ) -> RecommendationResponse:
        """Return popular movies for new users with no ratings."""
        popular = await self.movie_repo.get_popular(limit=limit)

        items = [
            RecommendationItem(
                movie_id=m.movie_id,
                title=m.title,
                genres=m.genres,
                year=m.year,
                poster_url=m.poster_url,
                avg_rating=m.avg_rating,
                rating_count=m.rating_count,
                predicted_rating=m.avg_rating,
                explanation="Popular movie",
                confidence=0.5,
                model_source="popular",
            )
            for m in popular
        ]

        return RecommendationResponse(
            user_id=user_id,
            recommendations=items,
            strategy="popular",
            generated_at=datetime.now(timezone.utc),
            latency_ms=0,
        )

    async def _get_content_based_fallback(
        self, user_id: int, limit: int
    ) -> RecommendationResponse:
        """Content-based recommendations for users with few ratings.

        Finds movies in genres the user has rated highly.
        """
        # Get user's rated movies to find preferred genres
        rated_ids = await self.rating_repo.get_user_rated_movie_ids(user_id)
        rated_movies = await self.movie_repo.get_by_movie_ids(list(rated_ids)) if rated_ids else []

        # Collect preferred genres from rated movies
        genre_counts: dict[str, int] = {}
        for m in rated_movies:
            if m.genres:
                for g in m.genres:
                    genre_counts[g] = genre_counts.get(g, 0) + 1

        # Get top genre
        top_genre = max(genre_counts, key=genre_counts.get) if genre_counts else None

        if top_genre:
            top_rated = await self.movie_repo.get_popular(limit=limit + len(rated_ids), genre=top_genre)
        else:
            top_rated = await self.movie_repo.get_top_rated(limit=limit + len(rated_ids))

        # Exclude already-rated movies
        top_rated = [m for m in top_rated if m.movie_id not in rated_ids][:limit]

        items = [
            RecommendationItem(
                movie_id=m.movie_id,
                title=m.title,
                genres=m.genres,
                year=m.year,
                poster_url=m.poster_url,
                avg_rating=m.avg_rating,
                rating_count=m.rating_count,
                predicted_rating=m.avg_rating,
                explanation=f"Popular in {top_genre}" if top_genre else "Highly rated movie",
                confidence=0.6,
                model_source="content_based",
            )
            for m in top_rated
        ]

        return RecommendationResponse(
            user_id=user_id,
            recommendations=items,
            strategy="content_based",
            generated_at=datetime.now(timezone.utc),
            latency_ms=0,
        )

    async def _get_collaborative_recommendations(
        self, user_id: int, limit: int
    ) -> RecommendationResponse:
        """Full collaborative filtering using ALS factor matrices.

        Scoring: predicted_rating(u, i) = dot(user_factors[u], item_factors[i])
        Excludes movies the user has already rated.
        """
        model = get_als_model()

        # Get user's already-rated movies
        rated_ids = await self.rating_repo.get_user_rated_movie_ids(user_id)

        if model.is_loaded and model.has_user(user_id):
            # Real ALS inference - constrain to movies in our DB
            db_movie_ids = await self.movie_repo.get_all_movie_ids()
            candidate_ids = list(db_movie_ids - rated_ids)

            predictions = model.predict_for_user(
                user_id=user_id,
                item_ids=candidate_ids,
                top_k=limit + 10,
                exclude_item_ids=rated_ids,
            )

            if predictions:
                # Fetch movie metadata for predicted items
                predicted_ids = [mid for mid, _ in predictions]
                score_map = dict(predictions)

                movies = await self.movie_repo.get_by_movie_ids(predicted_ids)
                movie_map = {m.movie_id: m for m in movies}

                items = []
                for mid in predicted_ids:
                    m = movie_map.get(mid)
                    if m is None:
                        continue
                    raw_score = score_map[mid]
                    # Clamp predicted rating to [0.5, 5.0]
                    pred_rating = max(0.5, min(5.0, raw_score))
                    confidence = min(1.0, abs(raw_score) / 5.0)

                    items.append(
                        RecommendationItem(
                            movie_id=m.movie_id,
                            title=m.title,
                            genres=m.genres,
                            year=m.year,
                            poster_url=m.poster_url,
                            avg_rating=m.avg_rating,
                            rating_count=m.rating_count,
                            predicted_rating=round(pred_rating, 2),
                            explanation="ALS collaborative filtering",
                            confidence=round(confidence, 2),
                            model_source="als",
                        )
                    )
                    if len(items) >= limit:
                        break

                if items:
                    return RecommendationResponse(
                        user_id=user_id,
                        recommendations=items,
                        strategy="collaborative",
                        generated_at=datetime.now(timezone.utc),
                        latency_ms=0,
                    )

        # Fallback: popular movies if model unavailable or user not in model
        logger.info(
            "collaborative_fallback",
            user_id=user_id,
            model_loaded=model.is_loaded,
            user_in_model=model.has_user(user_id) if model.is_loaded else False,
        )

        popular = await self.movie_repo.get_popular(limit=limit + len(rated_ids))
        popular = [m for m in popular if m.movie_id not in rated_ids][:limit]

        items = [
            RecommendationItem(
                movie_id=m.movie_id,
                title=m.title,
                genres=m.genres,
                year=m.year,
                poster_url=m.poster_url,
                avg_rating=m.avg_rating,
                rating_count=m.rating_count,
                predicted_rating=m.avg_rating,
                explanation="Popular movie (model fallback)",
                confidence=0.5,
                model_source="popular",
            )
            for m in popular
        ]

        return RecommendationResponse(
            user_id=user_id,
            recommendations=items,
            strategy="collaborative",
            generated_at=datetime.now(timezone.utc),
            latency_ms=0,
        )
