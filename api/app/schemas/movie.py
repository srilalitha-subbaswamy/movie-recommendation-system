"""Pydantic schemas for movie-related requests and responses."""

from datetime import datetime

from pydantic import BaseModel, Field


class MovieBase(BaseModel):
    """Base movie schema."""

    movie_id: int
    title: str
    genres: list[str] | None = None
    year: int | None = None


class MovieResponse(MovieBase):
    """Movie response with computed fields."""

    imdb_id: str | None = None
    tmdb_id: int | None = None
    poster_url: str | None = None
    avg_rating: float = 0.0
    rating_count: int = 0

    model_config = {"from_attributes": True}


class MovieListResponse(BaseModel):
    """Paginated list of movies."""

    movies: list[MovieResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class MovieSearchParams(BaseModel):
    """Query parameters for movie search."""

    query: str | None = Field(None, description="Search by title")
    genre: str | None = Field(None, description="Filter by genre")
    year_min: int | None = Field(None, ge=1900, description="Minimum release year")
    year_max: int | None = Field(None, le=2030, description="Maximum release year")
    min_rating: float | None = Field(None, ge=0, le=5, description="Minimum average rating")
    sort_by: str = Field("popularity", description="Sort field: popularity, rating, year, title")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")


class MovieDetail(MovieResponse):
    """Detailed movie response with additional fields."""

    created_at: datetime
    updated_at: datetime
