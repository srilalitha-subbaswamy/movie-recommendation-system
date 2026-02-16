"""Production database seeding script.

Creates tables, seeds movies from MovieLens, creates demo users,
seeds their ratings, and populates TMDB poster URLs.

Usage (inside the container or with PYTHONPATH=/app):
    python scripts/seed_production.py

Environment variables:
    DATABASE_URL  - PostgreSQL connection string (required)
    TMDB_API_KEY  - TMDB API key for poster fetching (optional)
"""

import asyncio
import csv
import json
import os
import re
import sys
import time
from pathlib import Path

# Demo users (must match frontend/src/context/UserContext.tsx)
DEMO_USERS = [
    (414, "user_414", 0, 0.0),
    (610, "user_610", 0, 0.0),
    (249, "user_249", 0, 0.0),
    (298, "user_298", 0, 0.0),
    (608, "user_608", 0, 0.0),
    (217, "user_217", 0, 0.0),
    (226, "user_226", 0, 0.0),
]
DEMO_USER_IDS = {u[0] for u in DEMO_USERS}

DATA_PATHS = [
    Path("data/raw/ml-latest-small"),
    Path("/app/data/raw/ml-latest-small"),
]


def find_data_path() -> Path:
    for p in DATA_PATHS:
        if p.exists() and (p / "movies.csv").exists():
            return p
    print("ERROR: MovieLens data not found at any expected path.")
    sys.exit(1)


def load_movies_csv(data_path: Path) -> list[dict]:
    movies = []
    with open(data_path / "movies.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            mid = int(row["movieId"])
            genres = row["genres"].split("|") if row["genres"] != "(no genres listed)" else []
            title = row["title"]
            year_match = re.search(r"\((\d{4})\)", title)
            year = int(year_match.group(1)) if year_match else None
            clean_title = re.sub(r"\s*\(\d{4}\)\s*$", "", title)
            movies.append({
                "movie_id": mid, "title": clean_title,
                "genres": genres, "year": year,
            })
    return movies


def load_links_csv(data_path: Path) -> dict[int, tuple[str, int | None]]:
    links = {}
    path = data_path / "links.csv"
    if not path.exists():
        return links
    with open(path) as f:
        for row in csv.DictReader(f):
            mid = int(row["movieId"])
            imdb = row.get("imdbId", "").strip()
            tmdb = row.get("tmdbId", "").strip()
            links[mid] = (imdb, int(tmdb) if tmdb else None)
    return links


def load_ratings_csv(data_path: Path) -> list[tuple[int, int, float]]:
    ratings = []
    with open(data_path / "ratings.csv") as f:
        for row in csv.DictReader(f):
            uid = int(row["userId"])
            mid = int(row["movieId"])
            rating = float(row["rating"])
            ratings.append((uid, mid, rating))
    return ratings


async def main():
    try:
        from app.core.database import async_session_factory, engine
    except ImportError:
        sys.path.insert(0, str(Path(__file__).parent.parent / "api"))
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from app.core.database import async_session_factory, engine

    from sqlalchemy import text

    data_path = find_data_path()
    print("=" * 60)
    print("Production Database Seeding")
    print(f"Data path: {data_path}")
    print("=" * 60)

    # ── Step 1: Create tables ────────────────────────────────
    print("\n[1/6] Creating tables...")
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS movies (
                id SERIAL PRIMARY KEY,
                movie_id INTEGER UNIQUE NOT NULL,
                title VARCHAR(500) NOT NULL,
                genres JSON,
                year INTEGER,
                imdb_id VARCHAR(20),
                tmdb_id INTEGER,
                poster_url VARCHAR(500),
                avg_rating FLOAT DEFAULT 0.0,
                rating_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW() NOT NULL,
                updated_at TIMESTAMP DEFAULT NOW() NOT NULL
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                user_id INTEGER UNIQUE NOT NULL,
                username VARCHAR(100),
                email VARCHAR(255),
                google_id VARCHAR(255),
                avatar_url VARCHAR(500),
                rating_count INTEGER DEFAULT 0,
                avg_rating FLOAT DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT NOW() NOT NULL,
                updated_at TIMESTAMP DEFAULT NOW() NOT NULL
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ratings (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                movie_id INTEGER NOT NULL,
                rating FLOAT NOT NULL,
                timestamp TIMESTAMP DEFAULT NOW() NOT NULL,
                CONSTRAINT uq_user_movie_rating UNIQUE (user_id, movie_id)
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_movies_movie_id ON movies(movie_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_movies_year ON movies(year)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ratings_user_id ON ratings(user_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ratings_movie_id ON ratings(movie_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ratings_timestamp ON ratings(timestamp)"))
        await conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_google_id ON users(google_id) WHERE google_id IS NOT NULL"
        ))
    print("  Tables created.")

    # ── Step 2: Seed movies ──────────────────────────────────
    print("\n[2/6] Seeding movies...")
    movies = load_movies_csv(data_path)
    links = load_links_csv(data_path)

    async with async_session_factory() as session:
        existing = await session.execute(text("SELECT COUNT(*) FROM movies"))
        count = existing.scalar()
        if count and count > 100:
            print(f"  Already {count} movies in DB, skipping movie seed.")
        else:
            for m in movies:
                imdb_id, tmdb_id = links.get(m["movie_id"], ("", None))
                await session.execute(
                    text("""
                        INSERT INTO movies (movie_id, title, genres, year, imdb_id, tmdb_id, avg_rating, rating_count)
                        VALUES (:mid, :title, CAST(:genres AS JSON), :year, :imdb_id, :tmdb_id, 0.0, 0)
                        ON CONFLICT (movie_id) DO NOTHING
                    """),
                    {
                        "mid": m["movie_id"], "title": m["title"],
                        "genres": json.dumps(m["genres"]), "year": m["year"],
                        "imdb_id": imdb_id or None, "tmdb_id": tmdb_id,
                    },
                )
            await session.commit()
            print(f"  Seeded {len(movies)} movies.")

    # ── Step 3: Create demo users ────────────────────────────
    print("\n[3/6] Creating demo users...")
    async with async_session_factory() as session:
        for uid, username, rc, ar in DEMO_USERS:
            await session.execute(
                text("""
                    INSERT INTO users (user_id, username, rating_count, avg_rating)
                    VALUES (:uid, :username, :rc, :ar)
                    ON CONFLICT (user_id) DO NOTHING
                """),
                {"uid": uid, "username": username, "rc": rc, "ar": ar},
            )
        await session.commit()
    print(f"  Created {len(DEMO_USERS)} demo users.")

    # ── Step 4: Seed demo user ratings ───────────────────────
    print("\n[4/6] Seeding demo user ratings...")
    all_ratings = load_ratings_csv(data_path)
    demo_ratings = [(u, m, r) for u, m, r in all_ratings if u in DEMO_USER_IDS]
    print(f"  Found {len(demo_ratings)} ratings for demo users in MovieLens")

    async with async_session_factory() as session:
        # Get movie IDs in DB
        result = await session.execute(text("SELECT movie_id FROM movies"))
        db_movie_ids = set(r[0] for r in result.fetchall())

        total = 0
        for uid in sorted(DEMO_USER_IDS):
            user_rats = [(m, r) for u, m, r in demo_ratings if u == uid and m in db_movie_ids]
            for mid, rating in user_rats:
                await session.execute(
                    text("""
                        INSERT INTO ratings (user_id, movie_id, rating)
                        VALUES (:uid, :mid, :rating)
                        ON CONFLICT ON CONSTRAINT uq_user_movie_rating DO UPDATE SET rating = EXCLUDED.rating
                    """),
                    {"uid": uid, "mid": mid, "rating": rating},
                )
            # Update user stats
            if user_rats:
                avg = sum(r for _, r in user_rats) / len(user_rats)
                await session.execute(
                    text("UPDATE users SET rating_count = :cnt, avg_rating = :avg WHERE user_id = :uid"),
                    {"uid": uid, "cnt": len(user_rats), "avg": round(avg, 2)},
                )
            total += len(user_rats)
            print(f"    User {uid}: {len(user_rats)} ratings")
        await session.commit()

    # Update movie aggregate stats
    async with async_session_factory() as session:
        await session.execute(text("""
            UPDATE movies SET
                rating_count = sub.cnt,
                avg_rating = sub.avg
            FROM (
                SELECT movie_id, COUNT(*) as cnt, ROUND(AVG(rating)::numeric, 2) as avg
                FROM ratings GROUP BY movie_id
            ) sub
            WHERE movies.movie_id = sub.movie_id
        """))
        await session.commit()
    print(f"  Seeded {total} total ratings. Updated movie stats.")

    # ── Step 5: Fetch TMDB posters ───────────────────────────
    tmdb_key = os.environ.get("TMDB_API_KEY", "")
    if tmdb_key:
        print("\n[5/6] Fetching TMDB poster URLs...")
        try:
            import httpx

            TMDB_BASE = "https://api.themoviedb.org/3"
            TMDB_IMG = "https://image.tmdb.org/t/p/w300"

            async with async_session_factory() as session:
                result = await session.execute(
                    text("SELECT movie_id, tmdb_id FROM movies WHERE poster_url IS NULL AND tmdb_id IS NOT NULL")
                )
                to_fetch = [(r[0], r[1]) for r in result.fetchall()]

            print(f"  {len(to_fetch)} movies need posters")
            posters = {}

            async with httpx.AsyncClient() as client:
                for i in range(0, len(to_fetch), 40):
                    batch = to_fetch[i:i + 40]
                    tasks = []
                    for movie_id, tmdb_id in batch:
                        tasks.append(client.get(
                            f"{TMDB_BASE}/movie/{tmdb_id}",
                            params={"api_key": tmdb_key}, timeout=10.0,
                        ))
                    responses = await asyncio.gather(*tasks, return_exceptions=True)
                    for (movie_id, _), resp in zip(batch, responses):
                        if isinstance(resp, Exception):
                            continue
                        if resp.status_code == 200:
                            poster_path = resp.json().get("poster_path")
                            if poster_path:
                                posters[movie_id] = f"{TMDB_IMG}{poster_path}"
                    print(f"    Fetched {min(i + 40, len(to_fetch))}/{len(to_fetch)} ({len(posters)} posters)")
                    if i + 40 < len(to_fetch):
                        time.sleep(1.5)

            if posters:
                async with async_session_factory() as session:
                    for mid, url in posters.items():
                        await session.execute(
                            text("UPDATE movies SET poster_url = :url WHERE movie_id = :mid"),
                            {"url": url, "mid": mid},
                        )
                    await session.commit()
                print(f"  Updated {len(posters)} movies with poster URLs.")
            else:
                print("  No posters fetched.")
        except ImportError:
            print("  httpx not available, skipping poster fetch.")
    else:
        print("\n[5/6] Skipping TMDB posters (TMDB_API_KEY not set)")

    # ── Step 6: Summary ──────────────────────────────────────
    print("\n[6/6] Final summary:")
    async with async_session_factory() as session:
        mc = (await session.execute(text("SELECT COUNT(*) FROM movies"))).scalar()
        uc = (await session.execute(text("SELECT COUNT(*) FROM users"))).scalar()
        rc = (await session.execute(text("SELECT COUNT(*) FROM ratings"))).scalar()
        pc = (await session.execute(text("SELECT COUNT(*) FROM movies WHERE poster_url IS NOT NULL"))).scalar()
        print(f"  Movies:  {mc}")
        print(f"  Users:   {uc}")
        print(f"  Ratings: {rc}")
        print(f"  Posters: {pc}")

    await engine.dispose()
    print("\n" + "=" * 60)
    print("Seeding complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
