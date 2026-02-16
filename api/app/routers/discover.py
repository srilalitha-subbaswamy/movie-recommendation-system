"""Semantic movie discovery endpoint."""

import time

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.embedding_index import get_movie_tags, is_loaded, search_by_description
from app.repositories.movie_repository import MovieRepository
from app.schemas.discover import DiscoverItem, DiscoverResponse

router = APIRouter(prefix="/discover", tags=["discover"])


@router.get("", response_model=DiscoverResponse)
async def discover_movies(
    q: str = Query(..., min_length=2, max_length=500, description="Natural language description"),
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    db: AsyncSession = Depends(get_db),
) -> DiscoverResponse:
    """Search movies by natural language description.

    Examples:
    - "light hearted comedies"
    - "dark psychological thriller"
    - "feel good family films"
    - "mind-bending sci-fi"
    - "classic noir detective stories"
    """
    start_time = time.monotonic()

    if not is_loaded():
        return DiscoverResponse(
            query=q,
            items=[],
            total=0,
            latency_ms=0,
        )

    # Semantic search
    results = search_by_description(q, top_k=limit + 10)

    if not results:
        elapsed = (time.monotonic() - start_time) * 1000
        return DiscoverResponse(query=q, items=[], total=0, latency_ms=round(elapsed, 2))

    # Fetch movie metadata from DB
    movie_ids = [mid for mid, _, _ in results]
    score_map = {mid: score for mid, score, _ in results}

    repo = MovieRepository(db)
    movies = await repo.get_by_movie_ids(movie_ids)
    movie_map = {m.movie_id: m for m in movies}

    items = []
    for mid in movie_ids:
        m = movie_map.get(mid)
        if m is None:
            continue
        tags = get_movie_tags(mid)
        items.append(
            DiscoverItem(
                movie_id=m.movie_id,
                title=m.title,
                genres=m.genres,
                year=m.year,
                poster_url=m.poster_url,
                avg_rating=m.avg_rating,
                rating_count=m.rating_count,
                relevance_score=round(score_map.get(mid, 0.0), 4),
                matched_tags=tags[:10],
            )
        )
        if len(items) >= limit:
            break

    elapsed = (time.monotonic() - start_time) * 1000
    return DiscoverResponse(
        query=q,
        items=items,
        total=len(items),
        latency_ms=round(elapsed, 2),
    )
