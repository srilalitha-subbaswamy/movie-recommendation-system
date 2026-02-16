"""Pydantic schemas for user-related requests and responses."""

from datetime import datetime

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    """User profile response."""

    user_id: int
    username: str | None = None
    email: str | None = None
    avatar_url: str | None = None
    rating_count: int = 0
    avg_rating: float = 0.0

    model_config = {"from_attributes": True}


class RatingCreate(BaseModel):
    """Schema for creating a new rating."""

    movie_id: int = Field(..., description="Movie ID to rate")
    rating: float = Field(..., ge=0.5, le=5.0, description="Rating value (0.5 to 5.0)")


class RatingResponse(BaseModel):
    """Rating response schema."""

    user_id: int
    movie_id: int
    rating: float
    timestamp: datetime

    model_config = {"from_attributes": True}


class RatingWithMovieResponse(BaseModel):
    """Rating with movie metadata."""

    user_id: int
    movie_id: int
    rating: float
    timestamp: datetime
    movie_title: str
    movie_genres: list[str] | None = None
    movie_year: int | None = None
    movie_poster_url: str | None = None
    movie_avg_rating: float = 0.0


class UserRatingsResponse(BaseModel):
    """Paginated list of user ratings."""

    user_id: int
    ratings: list[RatingResponse]
    total: int
    page: int
    page_size: int


class UserRatingStats(BaseModel):
    """Aggregate rating statistics for a user."""

    total_rated: int
    avg_rating: float
    rating_distribution: dict[str, int]
    genre_breakdown: dict[str, int]
