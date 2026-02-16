"""Seed real MovieLens ratings for demo users into the database.

Reads the downloaded MovieLens Small dataset and inserts actual ratings
for the 7 demo users, filtered to movies that exist in the DB.

Usage (run inside the API container or with DB access):
    python -m scripts.seed_demo_ratings

Or from the host:
    docker exec recsys-api python /app/scripts/seed_demo_ratings.py
"""

import asyncio
import csv
import json
import sys
from pathlib import Path

# Demo user IDs (must match frontend/src/context/UserContext.tsx)
DEMO_USER_IDS = {414, 610, 249, 298, 608, 217, 226}


def load_ratings_for_users(data_path: Path, user_ids: set[int]) -> dict[int, list[tuple[int, float]]]:
    """Load ratings from MovieLens CSV for specific users."""
    user_ratings: dict[int, list[tuple[int, float]]] = {uid: [] for uid in user_ids}

    with open(data_path / "ratings.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            uid = int(row["userId"])
            if uid in user_ids:
                mid = int(row["movieId"])
                rating = float(row["rating"])
                user_ratings[uid].append((mid, rating))

    return user_ratings


def load_movies(data_path: Path) -> dict[int, dict]:
    """Load movie metadata."""
    import re

    movies = {}
    with open(data_path / "movies.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mid = int(row["movieId"])
            genres = row["genres"].split("|") if row["genres"] != "(no genres listed)" else []
            title = row["title"]
            year_match = re.search(r"\((\d{4})\)", title)
            year = int(year_match.group(1)) if year_match else None
            clean_title = re.sub(r"\s*\(\d{4}\)\s*$", "", title)
            movies[mid] = {"title": clean_title, "genres": genres, "year": year}

    return movies


async def seed_ratings():
    """Seed demo user ratings into the database."""
    # Determine data path
    # When run inside Docker container, paths differ
    possible_paths = [
        Path("data/raw/ml-latest-small"),
        Path("/app/data/raw/ml-latest-small"),
    ]
    data_path = None
    for p in possible_paths:
        if p.exists():
            data_path = p
            break

    if data_path is None:
        print("ERROR: MovieLens data not found. Run 'python scripts/train_model.py' first.")
        sys.exit(1)

    # Import DB modules (works inside the API container)
    try:
        from app.core.database import async_session_factory, engine
    except ImportError:
        # Running from host - add api/ to path
        sys.path.insert(0, str(Path(__file__).parent.parent / "api"))
        from app.core.database import async_session_factory, engine

    from sqlalchemy import text

    print("=" * 60)
    print("Seeding Demo User Ratings from MovieLens")
    print("=" * 60)

    # Load ratings for demo users
    user_ratings = load_ratings_for_users(data_path, DEMO_USER_IDS)
    movies = load_movies(data_path)

    for uid, ratings in sorted(user_ratings.items()):
        print(f"  User {uid}: {len(ratings)} ratings in MovieLens")

    async with async_session_factory() as session:
        # Get movie IDs in our DB
        result = await session.execute(text("SELECT movie_id FROM movies"))
        db_movie_ids = set(r[0] for r in result.fetchall())
        print(f"\nDB has {len(db_movie_ids)} movies")

        # Also ensure all movies these users rated exist in our DB
        # Collect movie IDs that need to be added
        all_rated_movie_ids = set()
        for uid, ratings in user_ratings.items():
            for mid, _ in ratings:
                all_rated_movie_ids.add(mid)

        missing_movie_ids = all_rated_movie_ids - db_movie_ids
        print(f"Movies rated by demo users not in DB: {len(missing_movie_ids)}")

        # Add the most-rated missing movies (up to 500 more)
        # Count how many demo users rated each missing movie
        missing_counts: dict[int, int] = {}
        for uid, ratings in user_ratings.items():
            for mid, _ in ratings:
                if mid in missing_movie_ids:
                    missing_counts[mid] = missing_counts.get(mid, 0) + 1

        top_missing = sorted(missing_counts.keys(), key=lambda x: -missing_counts[x])[:500]

        if top_missing:
            print(f"Adding {len(top_missing)} additional movies to DB...")
            for mid in top_missing:
                if mid in movies:
                    m = movies[mid]
                    await session.execute(
                        text("""
                            INSERT INTO movies (movie_id, title, genres, year, avg_rating, rating_count)
                            VALUES (:movie_id, :title, CAST(:genres AS JSON), :year, 0.0, 0)
                            ON CONFLICT (movie_id) DO NOTHING
                        """),
                        {
                            "movie_id": mid,
                            "title": m["title"],
                            "genres": json.dumps(m["genres"]),
                            "year": m["year"],
                        },
                    )
            db_movie_ids.update(top_missing)

        # Insert ratings for each demo user
        total_inserted = 0
        for uid in sorted(DEMO_USER_IDS):
            ratings = user_ratings[uid]
            # Filter to movies in DB
            valid_ratings = [(mid, r) for mid, r in ratings if mid in db_movie_ids]

            count = 0
            for mid, rating in valid_ratings:
                await session.execute(
                    text("""
                        INSERT INTO ratings (user_id, movie_id, rating)
                        VALUES (:user_id, :movie_id, :rating)
                        ON CONFLICT ON CONSTRAINT uq_user_movie_rating DO UPDATE SET
                            rating = EXCLUDED.rating
                    """),
                    {"user_id": uid, "movie_id": mid, "rating": rating},
                )
                count += 1

            # Update user stats
            avg = sum(r for _, r in valid_ratings) / len(valid_ratings) if valid_ratings else 0
            await session.execute(
                text("""
                    UPDATE users SET rating_count = :count, avg_rating = :avg
                    WHERE user_id = :uid
                """),
                {"uid": uid, "count": count, "avg": round(avg, 2)},
            )

            print(f"  User {uid}: inserted {count} ratings (avg: {avg:.2f})")
            total_inserted += count

        await session.commit()

    # Update movie aggregate stats
    async with async_session_factory() as session:
        await session.execute(text("""
            UPDATE movies SET
                rating_count = sub.cnt,
                avg_rating = sub.avg
            FROM (
                SELECT movie_id, COUNT(*) as cnt, ROUND(AVG(rating)::numeric, 2) as avg
                FROM ratings
                GROUP BY movie_id
            ) sub
            WHERE movies.movie_id = sub.movie_id
        """))
        await session.commit()
        print(f"\nUpdated movie aggregate stats")

    await engine.dispose()

    print(f"\nTotal: {total_inserted} ratings seeded for {len(DEMO_USER_IDS)} demo users")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(seed_ratings())
