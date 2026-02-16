"""Recommendation API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.movie_repository import MovieRepository
from app.repositories.rating_repository import RatingRepository
from app.repositories.user_repository import UserRepository
from app.schemas.recommendation import RecommendationResponse, SimilarMoviesResponse
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def get_recommendation_service(
    db: AsyncSession = Depends(get_db),
) -> RecommendationService:
    """Dependency injection for RecommendationService."""
    return RecommendationService(
        user_repo=UserRepository(db),
        movie_repo=MovieRepository(db),
        rating_repo=RatingRepository(db),
    )


@router.get("/{user_id}", response_model=RecommendationResponse)
async def get_recommendations(
    user_id: int,
    limit: int = Query(20, ge=1, le=100, description="Number of recommendations"),
    explain: bool = Query(False, description="Include explanations"),
    service: RecommendationService = Depends(get_recommendation_service),
) -> RecommendationResponse:
    """Get personalized movie recommendations for a user.

    Implements tiered strategy:
    - New users (0 ratings): popular movies
    - Few ratings (<5): content-based fallback
    - Active users (5+): collaborative filtering
    """
    return await service.get_recommendations(
        user_id=user_id, limit=limit, explain=explain
    )


@router.get("/similar/{movie_id}", response_model=SimilarMoviesResponse)
async def get_similar_movies(
    movie_id: int,
    limit: int = Query(10, ge=1, le=50, description="Number of similar movies"),
    service: RecommendationService = Depends(get_recommendation_service),
) -> SimilarMoviesResponse:
    """Get movies similar to a given movie."""
    return await service.get_similar_movies(movie_id=movie_id, limit=limit)
