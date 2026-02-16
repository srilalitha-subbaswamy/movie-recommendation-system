"""Seed the database with sample movie data for development.

This script populates the database with a curated set of popular movies
and sample users for local development and demo purposes.
"""

import asyncio
import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory, engine

# Sample movies (movie_id, title, genres, year, avg_rating, rating_count)
SAMPLE_MOVIES = [
    (1, "Toy Story", ["Animation", "Children", "Comedy", "Fantasy"], 1995, 3.89, 73215),
    (2, "Jumanji", ["Adventure", "Children", "Fantasy"], 1995, 3.21, 31078),
    (296, "Pulp Fiction", ["Comedy", "Crime", "Drama", "Thriller"], 1994, 4.20, 92406),
    (318, "The Shawshank Redemption", ["Crime", "Drama"], 1994, 4.43, 97999),
    (356, "Forrest Gump", ["Comedy", "Drama", "Romance", "War"], 1994, 4.03, 92174),
    (480, "Jurassic Park", ["Action", "Adventure", "Sci-Fi", "Thriller"], 1993, 3.66, 64144),
    (527, "Schindler's List", ["Drama", "War"], 1993, 4.31, 60411),
    (589, "Terminator 2: Judgment Day", ["Action", "Sci-Fi"], 1991, 3.93, 62104),
    (593, "Silence of the Lambs", ["Crime", "Horror", "Thriller"], 1991, 4.16, 74127),
    (608, "Fargo", ["Comedy", "Crime", "Drama", "Thriller"], 1996, 4.07, 55509),
    (858, "The Godfather", ["Crime", "Drama"], 1972, 4.36, 60904),
    (1196, "Star Wars: Episode V", ["Action", "Adventure", "Drama", "Sci-Fi"], 1980, 4.19, 72684),
    (1198, "Raiders of the Lost Ark", ["Action", "Adventure"], 1981, 4.13, 65261),
    (1270, "Back to the Future", ["Adventure", "Comedy", "Sci-Fi"], 1985, 3.96, 62591),
    (2571, "The Matrix", ["Action", "Sci-Fi", "Thriller"], 1999, 4.19, 84545),
    (2959, "Fight Club", ["Action", "Crime", "Drama", "Thriller"], 1999, 4.23, 72781),
    (4993, "The Lord of the Rings: The Fellowship of the Ring", ["Adventure", "Fantasy"], 2001, 4.11, 66870),
    (4995, "A Beautiful Mind", ["Drama", "Romance"], 2001, 3.88, 43358),
    (5952, "The Lord of the Rings: The Two Towers", ["Adventure", "Fantasy"], 2002, 4.03, 56314),
    (7153, "The Lord of the Rings: The Return of the King", ["Action", "Adventure", "Drama", "Fantasy"], 2003, 4.12, 56884),
    (7361, "Eternal Sunshine of the Spotless Mind", ["Drama", "Romance", "Sci-Fi"], 2004, 4.08, 47285),
    (8961, "The Incredibles", ["Action", "Adventure", "Animation", "Children", "Comedy"], 2004, 3.88, 41671),
    (33794, "The Dark Knight", ["Action", "Crime", "Drama", "IMAX"], 2008, 4.24, 55366),
    (58559, "The Dark Knight", ["Action", "Crime", "Drama", "IMAX"], 2008, 4.24, 55366),
    (59315, "WALL-E", ["Adventure", "Animation", "Children", "Comedy", "Fantasy", "Romance", "Sci-Fi"], 2008, 4.05, 39945),
    (68157, "Inglourious Basterds", ["Action", "Drama", "War"], 2009, 4.01, 35429),
    (79132, "Inception", ["Action", "Crime", "Drama", "Mystery", "Sci-Fi", "Thriller", "IMAX"], 2010, 4.15, 52366),
    (91529, "Django Unchained", ["Action", "Drama", "Western"], 2012, 4.09, 32753),
    (99114, "Django Unchained", ["Action", "Drama", "Western"], 2012, 4.09, 32753),
    (109487, "Interstellar", ["Sci-Fi", "IMAX"], 2014, 4.11, 33836),
    (112552, "Whiplash", ["Drama"], 2014, 4.28, 18753),
    (122882, "Mad Max: Fury Road", ["Action", "Adventure", "Sci-Fi", "Thriller"], 2015, 4.06, 17907),
    (134130, "The Martian", ["Adventure", "Drama", "Sci-Fi"], 2015, 3.92, 18154),
    (168252, "Logan", ["Action", "Sci-Fi"], 2017, 4.01, 10156),
    (170875, "The Shape of Water", ["Adventure", "Drama", "Fantasy", "Thriller"], 2017, 3.68, 6482),
    (176371, "Blade Runner 2049", ["Sci-Fi", "Thriller"], 2017, 3.97, 7549),
    (193587, "Avengers: Endgame", ["Action", "Adventure", "Drama", "Sci-Fi"], 2019, 4.15, 3217),
    (193609, "Spider-Man: Into the Spider-Verse", ["Action", "Adventure", "Animation", "Sci-Fi"], 2018, 4.24, 3154),
]

# Sample users (user_id, username, rating_count, avg_rating)
SAMPLE_USERS = [
    (1, "alice", 232, 3.62),
    (2, "bob", 29, 3.40),
    (3, "charlie", 51, 4.18),
    (4, "diana", 5, 3.90),
    (5, "eve", 0, 0.0),
    (6, "frank", 147, 3.55),
    (7, "grace", 88, 4.02),
    (8, "henry", 12, 3.75),
    (9, "ivy", 310, 3.44),
    (10, "jack", 3, 4.33),
]


async def seed_movies(session: AsyncSession) -> None:
    """Insert sample movies."""
    # De-duplicate by movie_id
    seen = set()
    unique_movies = []
    for m in SAMPLE_MOVIES:
        if m[0] not in seen:
            seen.add(m[0])
            unique_movies.append(m)

    for movie_id, title, genres, year, avg_rating, rating_count in unique_movies:
        await session.execute(
            text("""
                INSERT INTO movies (movie_id, title, genres, year, avg_rating, rating_count)
                VALUES (:movie_id, :title, CAST(:genres AS JSON), :year, :avg_rating, :rating_count)
                ON CONFLICT (movie_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    avg_rating = EXCLUDED.avg_rating,
                    rating_count = EXCLUDED.rating_count
            """),
            {
                "movie_id": movie_id,
                "title": title,
                "genres": json.dumps(genres),
                "year": year,
                "avg_rating": avg_rating,
                "rating_count": rating_count,
            },
        )
    print(f"  Seeded {len(unique_movies)} movies")


async def seed_users(session: AsyncSession) -> None:
    """Insert sample users."""
    for user_id, username, rating_count, avg_rating in SAMPLE_USERS:
        await session.execute(
            text("""
                INSERT INTO users (user_id, username, rating_count, avg_rating)
                VALUES (:user_id, :username, :rating_count, :avg_rating)
                ON CONFLICT (user_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    rating_count = EXCLUDED.rating_count,
                    avg_rating = EXCLUDED.avg_rating
            """),
            {
                "user_id": user_id,
                "username": username,
                "rating_count": rating_count,
                "avg_rating": avg_rating,
            },
        )
    print(f"  Seeded {len(SAMPLE_USERS)} users")


async def seed_ratings(session: AsyncSession) -> None:
    """Insert sample ratings for users."""
    sample_ratings = [
        (1, 318, 5.0), (1, 296, 4.5), (1, 2571, 4.0), (1, 858, 5.0), (1, 527, 4.5),
        (2, 1, 3.0), (2, 356, 4.0), (2, 480, 3.5),
        (3, 318, 5.0), (3, 858, 5.0), (3, 2959, 4.5), (3, 79132, 4.0),
        (6, 318, 4.5), (6, 296, 4.0), (6, 2571, 5.0), (6, 79132, 4.5),
        (7, 1, 4.0), (7, 593, 4.5), (7, 608, 4.0), (7, 33794, 5.0),
    ]

    for user_id, movie_id, rating in sample_ratings:
        await session.execute(
            text("""
                INSERT INTO ratings (user_id, movie_id, rating)
                VALUES (:user_id, :movie_id, :rating)
                ON CONFLICT ON CONSTRAINT uq_user_movie_rating DO UPDATE SET
                    rating = EXCLUDED.rating
            """),
            {"user_id": user_id, "movie_id": movie_id, "rating": rating},
        )
    print(f"  Seeded {len(sample_ratings)} ratings")


async def main() -> None:
    """Run database seeding."""
    print("=" * 60)
    print("Seeding Database")
    print("=" * 60)

    async with async_session_factory() as session:
        await seed_movies(session)
        await seed_users(session)
        await seed_ratings(session)
        await session.commit()

    await engine.dispose()

    print("")
    print("Database seeded successfully!")


if __name__ == "__main__":
    asyncio.run(main())
