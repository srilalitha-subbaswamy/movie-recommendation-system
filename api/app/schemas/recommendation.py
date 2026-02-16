"""Pydantic schemas for recommendation responses."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class RecommendationItem(BaseModel):
    """A single recommendation with explanation."""

    movie_id: int
    title: str
    genres: list[str] | None = None
    year: int | None = None
    poster_url: str | None = None
    avg_rating: float = 0.0
    rating_count: int = 0
    predicted_rating: float
    explanation: str
    confidence: float
    model_source: Literal["als", "ncf", "ensemble", "popular", "content_based"]


class RecommendationResponse(BaseModel):
    """Full recommendation response."""

    user_id: int
    recommendations: list[RecommendationItem]
    strategy: Literal["collaborative", "content_based", "popular", "hybrid"]
    generated_at: datetime
    latency_ms: float
    cached: bool = False


class SimilarMoviesResponse(BaseModel):
    """Response for similar movies endpoint."""

    movie_id: int
    title: str
    similar_movies: list[RecommendationItem]
    generated_at: datetime
    latency_ms: float
