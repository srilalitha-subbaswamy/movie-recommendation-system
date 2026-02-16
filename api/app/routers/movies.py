"""Movie catalog API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.movie_repository import MovieRepository
from app.schemas.movie import MovieDetail, MovieListResponse, MovieResponse, MovieSearchParams
from app.services.movie_service import MovieService

router = APIRouter(prefix="/movies", tags=["movies"])


def get_movie_service(db: AsyncSession = Depends(get_db)) -> MovieService:
    """Dependency injection for MovieService."""
    return MovieService(movie_repo=MovieRepository(db))


@router.get("", response_model=MovieListResponse)
async def search_movies(
    query: str | None = Query(None, description="Search by title"),
    genre: str | None = Query(None, description="Filter by genre"),
    year_min: int | None = Query(None, ge=1900, description="Minimum release year"),
    year_max: int | None = Query(None, le=2030, description="Maximum release year"),
    min_rating: float | None = Query(None, ge=0, le=5, description="Minimum average rating"),
    sort_by: str = Query("popularity", description="Sort: popularity, rating, year, title"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    service: MovieService = Depends(get_movie_service),
) -> MovieListResponse:
    """Search and browse the movie catalog with filtering and pagination."""
    params = MovieSearchParams(
        query=query,
        genre=genre,
        year_min=year_min,
        year_max=year_max,
        min_rating=min_rating,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )
    return await service.search_movies(params)


@router.get("/popular", response_model=list[MovieResponse])
async def get_popular_movies(
    limit: int = Query(20, ge=1, le=100, description="Number of movies to return"),
    genre: str | None = Query(None, description="Filter by genre"),
    service: MovieService = Depends(get_movie_service),
) -> list[MovieResponse]:
    """Get popular movies, optionally filtered by genre."""
    return await service.get_popular_movies(limit=limit, genre=genre)


@router.get("/{movie_id}", response_model=MovieDetail)
async def get_movie(
    movie_id: int,
    service: MovieService = Depends(get_movie_service),
) -> MovieDetail:
    """Get detailed information for a specific movie."""
    return await service.get_movie(movie_id)
