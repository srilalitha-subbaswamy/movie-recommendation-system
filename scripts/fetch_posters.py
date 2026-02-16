"""Fetch movie poster URLs from TMDB API and store in the database.

Uses the links.csv file from MovieLens to map movieId -> tmdbId,
then fetches poster_path from TMDB and builds the full image URL.

Usage:
    TMDB_API_KEY=your_key python scripts/fetch_posters.py

Or inside Docker:
    docker exec -e TMDB_API_KEY=your_key -e PYTHONPATH=/app recsys-api python scripts/fetch_posters.py
"""

import asyncio
import csv
import os
import sys
import time
from pathlib import Path

import httpx

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w300"
BATCH_SIZE = 40  # TMDB rate limit: ~40 req/sec on free tier
SLEEP_BETWEEN_BATCHES = 1.5  # seconds


def load_links(data_path: Path) -> dict[int, int]:
    """Load movieId -> tmdbId mapping from links.csv."""
    links = {}
    with open(data_path / "links.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            movie_id = int(row["movieId"])
            tmdb_id = row.get("tmdbId", "").strip()
            if tmdb_id:
                links[movie_id] = int(tmdb_id)
    return links


async def fetch_poster_url(client: httpx.AsyncClient, tmdb_id: int, api_key: str) -> str | None:
    """Fetch poster URL for a single movie from TMDB."""
    try:
        resp = await client.get(
            f"{TMDB_BASE_URL}/movie/{tmdb_id}",
            params={"api_key": api_key},
            timeout=10.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            poster_path = data.get("poster_path")
            if poster_path:
                return f"{TMDB_IMAGE_BASE}{poster_path}"
        elif resp.status_code == 404:
            return None
        else:
            return None
    except Exception:
        return None


async def fetch_batch(
    client: httpx.AsyncClient,
    batch: list[tuple[int, int]],
    api_key: str,
) -> dict[int, str]:
    """Fetch posters for a batch of movies concurrently."""
    tasks = []
    for movie_id, tmdb_id in batch:
        tasks.append(fetch_poster_url(client, tmdb_id, api_key))

    results = await asyncio.gather(*tasks)
    poster_map = {}
    for (movie_id, _), poster_url in zip(batch, results):
        if poster_url:
            poster_map[movie_id] = poster_url
    return poster_map


async def main():
    api_key = os.environ.get("TMDB_API_KEY", "")
    if not api_key:
        print("ERROR: TMDB_API_KEY environment variable not set.")
        print("Get a free key at: https://www.themoviedb.org/settings/api")
        sys.exit(1)

    # Find data path
    possible_paths = [
        Path("data/raw/ml-latest-small"),
        Path("/app/data/raw/ml-latest-small"),
    ]
    data_path = None
    for p in possible_paths:
        if p.exists():
            data_path = p
            break
    if not data_path:
        print("ERROR: MovieLens data not found.")
        sys.exit(1)

    # Import DB
    try:
        from app.core.database import async_session_factory, engine
    except ImportError:
        sys.path.insert(0, str(Path(__file__).parent.parent / "api"))
        from app.core.database import async_session_factory, engine

    from sqlalchemy import text

    print("=" * 60)
    print("Fetching Movie Posters from TMDB")
    print("=" * 60)

    # Load links
    links = load_links(data_path)
    print(f"Loaded {len(links)} movieId->tmdbId mappings")

    # Get movies from DB that need posters
    async with async_session_factory() as session:
        result = await session.execute(
            text("SELECT movie_id FROM movies WHERE poster_url IS NULL")
        )
        db_movie_ids = [r[0] for r in result.fetchall()]

    # Filter to movies we have TMDB IDs for
    to_fetch = [(mid, links[mid]) for mid in db_movie_ids if mid in links]
    print(f"Movies needing posters: {len(db_movie_ids)}")
    print(f"Movies with TMDB IDs: {len(to_fetch)}")

    if not to_fetch:
        print("Nothing to fetch!")
        await engine.dispose()
        return

    # Fetch in batches
    all_posters: dict[int, str] = {}
    async with httpx.AsyncClient() as client:
        for i in range(0, len(to_fetch), BATCH_SIZE):
            batch = to_fetch[i : i + BATCH_SIZE]
            batch_posters = await fetch_batch(client, batch, api_key)
            all_posters.update(batch_posters)

            fetched = i + len(batch)
            found = len(all_posters)
            print(f"  Fetched {fetched}/{len(to_fetch)} ({found} posters found)")

            if i + BATCH_SIZE < len(to_fetch):
                time.sleep(SLEEP_BETWEEN_BATCHES)

    print(f"\nTotal posters found: {len(all_posters)}")

    # Update DB
    if all_posters:
        async with async_session_factory() as session:
            for movie_id, poster_url in all_posters.items():
                await session.execute(
                    text("UPDATE movies SET poster_url = :url WHERE movie_id = :mid"),
                    {"url": poster_url, "mid": movie_id},
                )
            # Also update tmdb_id for movies that have it
            for movie_id, tmdb_id in to_fetch:
                await session.execute(
                    text("UPDATE movies SET tmdb_id = :tid WHERE movie_id = :mid AND tmdb_id IS NULL"),
                    {"tid": tmdb_id, "mid": movie_id},
                )
            await session.commit()
        print(f"Updated {len(all_posters)} movies with poster URLs")

    await engine.dispose()
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
