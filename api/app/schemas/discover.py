"""Pydantic schemas for the discover/semantic search endpoint."""

from pydantic import BaseModel


class DiscoverItem(BaseModel):
    """A single discovery result with relevance info."""

    movie_id: int
    title: str
    genres: list[str] | None = None
    year: int | None = None
    poster_url: str | None = None
    avg_rating: float = 0.0
    rating_count: int = 0
    relevance_score: float
    matched_tags: list[str]

    model_config = {"from_attributes": True}


class DiscoverResponse(BaseModel):
    """Response for semantic movie search."""

    query: str
    items: list[DiscoverItem]
    total: int
    latency_ms: float
