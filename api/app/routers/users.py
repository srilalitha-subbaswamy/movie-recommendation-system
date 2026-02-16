"""User API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import UserNotFoundException
from app.repositories.rating_repository import RatingRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    RatingCreate,
    RatingResponse,
    RatingWithMovieResponse,
    UserRatingStats,
    UserRatingsResponse,
    UserResponse,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Get user profile."""
    repo = UserRepository(db)
    user = await repo.get_by_user_id(user_id)
    if not user:
        raise UserNotFoundException(user_id)
    return UserResponse.model_validate(user)


@router.get("/{user_id}/ratings")
async def get_user_ratings(
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a user's rating history with movie metadata."""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_user_id(user_id)
    if not user:
        raise UserNotFoundException(user_id)

    rating_repo = RatingRepository(db)
    ratings_with_movies, total = await rating_repo.get_user_ratings_with_movies(
        user_id=user_id, page=page, page_size=page_size
    )

    return {
        "user_id": user_id,
        "ratings": ratings_with_movies,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{user_id}/ratings/movie/{movie_id}", response_model=RatingResponse | None)
async def get_user_rating_for_movie(
    user_id: int,
    movie_id: int,
    db: AsyncSession = Depends(get_db),
) -> RatingResponse | None:
    """Get a user's rating for a specific movie. Returns null if not rated."""
    rating_repo = RatingRepository(db)
    rating = await rating_repo.get_user_rating_for_movie(user_id, movie_id)
    if not rating:
        return None
    return RatingResponse.model_validate(rating)


@router.get("/{user_id}/ratings/stats", response_model=UserRatingStats)
async def get_user_rating_stats(
    user_id: int,
    db: AsyncSession = Depends(get_db),
) -> UserRatingStats:
    """Get aggregate rating statistics for a user.

    Returns total rated, average rating, rating distribution, and genre breakdown.
    """
    user_repo = UserRepository(db)
    user = await user_repo.get_by_user_id(user_id)
    if not user:
        raise UserNotFoundException(user_id)

    rating_repo = RatingRepository(db)
    stats = await rating_repo.get_user_rating_stats(user_id)
    return UserRatingStats(**stats)


@router.post("/{user_id}/ratings", response_model=RatingResponse, status_code=201)
async def create_rating(
    user_id: int,
    rating_data: RatingCreate,
    db: AsyncSession = Depends(get_db),
) -> RatingResponse:
    """Submit a movie rating for a user."""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_user_id(user_id)
    if not user:
        raise UserNotFoundException(user_id)

    rating_repo = RatingRepository(db)
    rating = await rating_repo.create(
        user_id=user_id,
        movie_id=rating_data.movie_id,
        rating=rating_data.rating,
    )

    return RatingResponse.model_validate(rating)


@router.delete("/{user_id}/ratings/{movie_id}", status_code=204)
async def delete_rating(
    user_id: int,
    movie_id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a rating for a specific movie."""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_user_id(user_id)
    if not user:
        raise UserNotFoundException(user_id)

    rating_repo = RatingRepository(db)
    deleted = await rating_repo.delete(user_id, movie_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Rating not found")
