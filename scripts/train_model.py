"""Download MovieLens Small, train ALS model, export factor matrices.

This is a lightweight alternative to the full Spark pipeline.
Uses scipy sparse matrices and numpy for ALS training.
Works on MovieLens Small (100K ratings, ~1MB download).

Usage:
    python scripts/train_model.py

Outputs:
    models/als/user_factors.npy   - User factor matrix (n_users x rank)
    models/als/item_factors.npy   - Item factor matrix (n_items x rank)
    models/als/user_id_map.npy    - Mapping from matrix row -> userId
    models/als/item_id_map.npy    - Mapping from matrix col -> movieId
    models/als/metadata.json      - Model metadata (rank, rmse, etc.)
"""

import json
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

import numpy as np

# ─── Configuration ────────────────────────────────────────────────────────────

DATASET_URL = "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip"
DATA_DIR = Path("data/raw")
MODEL_DIR = Path("models/als")
RANK = 50  # Number of latent factors
ITERATIONS = 15  # ALS iterations
REGULARIZATION = 0.1  # L2 regularization
RANDOM_SEED = 42


# ─── Download ─────────────────────────────────────────────────────────────────

def download_dataset() -> Path:
    """Download MovieLens Small if not already present."""
    data_path = DATA_DIR / "ml-latest-small"
    if data_path.exists():
        print(f"Dataset already exists at {data_path}")
        return data_path

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = DATA_DIR / "ml-latest-small.zip"

    print(f"Downloading MovieLens Small (~1MB)...")
    urllib.request.urlretrieve(DATASET_URL, zip_path)

    print("Extracting...")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(DATA_DIR)

    zip_path.unlink()
    print(f"Dataset extracted to {data_path}")
    return data_path


# ─── Load Data ────────────────────────────────────────────────────────────────

def load_ratings(data_path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Load ratings.csv into numpy arrays."""
    print("Loading ratings...")
    ratings = []
    with open(data_path / "ratings.csv") as f:
        next(f)  # skip header
        for line in f:
            parts = line.strip().split(",")
            user_id = int(parts[0])
            movie_id = int(parts[1])
            rating = float(parts[2])
            ratings.append((user_id, movie_id, rating))

    data = np.array(ratings)
    print(f"  Loaded {len(data)} ratings")
    return data[:, 0].astype(int), data[:, 1].astype(int), data[:, 2]


def load_movies(data_path: Path) -> dict[int, dict]:
    """Load movies.csv into a dict of movieId -> {title, genres}."""
    movies = {}
    with open(data_path / "movies.csv", encoding="utf-8") as f:
        next(f)  # skip header
        for line in f:
            # Handle commas in movie titles by splitting carefully
            parts = line.strip().split(",")
            movie_id = int(parts[0])
            # Genres is always last, title is everything in between
            genres = parts[-1]
            title = ",".join(parts[1:-1]).strip('"')
            movies[movie_id] = {
                "title": title,
                "genres": genres.split("|") if genres != "(no genres listed)" else [],
            }
    print(f"  Loaded {len(movies)} movies")
    return movies


# ─── ALS Training ─────────────────────────────────────────────────────────────

def train_als(
    user_ids: np.ndarray,
    item_ids: np.ndarray,
    ratings: np.ndarray,
    rank: int = RANK,
    iterations: int = ITERATIONS,
    reg: float = REGULARIZATION,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict]:
    """Train ALS collaborative filtering model.

    Alternating Least Squares:
    1. Fix item factors, solve for user factors
    2. Fix user factors, solve for item factors
    3. Repeat until convergence

    Args:
        user_ids: Array of user IDs from ratings
        item_ids: Array of item IDs from ratings
        ratings: Array of rating values
        rank: Number of latent factors
        iterations: Number of ALS iterations
        reg: L2 regularization parameter

    Returns:
        user_factors, item_factors, user_id_map, item_id_map, metrics
    """
    np.random.seed(RANDOM_SEED)

    # Create ID mappings (original ID -> matrix index)
    unique_users = np.unique(user_ids)
    unique_items = np.unique(item_ids)
    user_to_idx = {uid: idx for idx, uid in enumerate(unique_users)}
    item_to_idx = {iid: idx for idx, iid in enumerate(unique_items)}

    n_users = len(unique_users)
    n_items = len(unique_items)
    n_ratings = len(ratings)

    print(f"\nTraining ALS model:")
    print(f"  Users: {n_users}, Items: {n_items}, Ratings: {n_ratings}")
    print(f"  Rank: {rank}, Iterations: {iterations}, Reg: {reg}")
    print(f"  Sparsity: {1 - n_ratings / (n_users * n_items):.4%}")

    # Map to matrix indices
    row_idx = np.array([user_to_idx[u] for u in user_ids])
    col_idx = np.array([item_to_idx[i] for i in item_ids])

    # Initialize factors randomly
    user_factors = np.random.normal(0, 0.1, (n_users, rank))
    item_factors = np.random.normal(0, 0.1, (n_items, rank))

    # Build user->ratings and item->ratings lookup for efficiency
    user_ratings: dict[int, list[tuple[int, float]]] = {i: [] for i in range(n_users)}
    item_ratings: dict[int, list[tuple[int, float]]] = {i: [] for i in range(n_items)}

    for idx in range(n_ratings):
        u, i, r = row_idx[idx], col_idx[idx], ratings[idx]
        user_ratings[u].append((i, r))
        item_ratings[i].append((u, r))

    reg_eye = reg * np.eye(rank)

    # ALS iterations
    for iteration in range(iterations):
        # Fix items, solve for users
        for u in range(n_users):
            if not user_ratings[u]:
                continue
            items_u = [x[0] for x in user_ratings[u]]
            ratings_u = np.array([x[1] for x in user_ratings[u]])
            V = item_factors[items_u]  # (n_rated x rank)
            # user_factors[u] = (V^T V + λI)^{-1} V^T r
            A = V.T @ V + reg_eye
            b = V.T @ ratings_u
            user_factors[u] = np.linalg.solve(A, b)

        # Fix users, solve for items
        for i in range(n_items):
            if not item_ratings[i]:
                continue
            users_i = [x[0] for x in item_ratings[i]]
            ratings_i = np.array([x[1] for x in item_ratings[i]])
            U = user_factors[users_i]  # (n_rated x rank)
            A = U.T @ U + reg_eye
            b = U.T @ ratings_i
            item_factors[i] = np.linalg.solve(A, b)

        # Compute RMSE
        predictions = np.sum(user_factors[row_idx] * item_factors[col_idx], axis=1)
        rmse = np.sqrt(np.mean((ratings - predictions) ** 2))
        print(f"  Iteration {iteration + 1}/{iterations} - RMSE: {rmse:.4f}")

    # Final metrics
    predictions = np.sum(user_factors[row_idx] * item_factors[col_idx], axis=1)
    final_rmse = float(np.sqrt(np.mean((ratings - predictions) ** 2)))
    mae = float(np.mean(np.abs(ratings - predictions)))

    metrics = {
        "rmse": round(final_rmse, 4),
        "mae": round(mae, 4),
        "n_users": n_users,
        "n_items": n_items,
        "n_ratings": n_ratings,
        "rank": rank,
        "iterations": iterations,
        "regularization": reg,
    }

    print(f"\n  Final RMSE: {final_rmse:.4f}, MAE: {mae:.4f}")

    return user_factors, item_factors, unique_users, unique_items, metrics


# ─── Export ───────────────────────────────────────────────────────────────────

def export_model(
    user_factors: np.ndarray,
    item_factors: np.ndarray,
    user_ids: np.ndarray,
    item_ids: np.ndarray,
    metrics: dict,
    movies: dict[int, dict],
) -> None:
    """Save model artifacts to disk."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    np.save(MODEL_DIR / "user_factors.npy", user_factors)
    np.save(MODEL_DIR / "item_factors.npy", item_factors)
    np.save(MODEL_DIR / "user_id_map.npy", user_ids)
    np.save(MODEL_DIR / "item_id_map.npy", item_ids)

    with open(MODEL_DIR / "metadata.json", "w") as f:
        json.dump(metrics, f, indent=2)

    # Also save a movie lookup for explanations
    movie_lookup = {}
    for mid in item_ids:
        mid = int(mid)
        if mid in movies:
            movie_lookup[mid] = movies[mid]
    with open(MODEL_DIR / "movie_lookup.json", "w") as f:
        json.dump(movie_lookup, f, indent=2, ensure_ascii=False)

    print(f"\nModel exported to {MODEL_DIR}/")
    print(f"  user_factors.npy: {user_factors.shape}")
    print(f"  item_factors.npy: {item_factors.shape}")


# ─── Seed Database ────────────────────────────────────────────────────────────

def generate_seed_sql(
    data_path: Path,
    movies: dict[int, dict],
    user_ids: np.ndarray,
    item_ids: np.ndarray,
    all_user_ids: np.ndarray,
    all_item_ids: np.ndarray,
    all_ratings: np.ndarray,
) -> None:
    """Generate a SQL seed file for the top movies and active users."""
    import json as json_mod

    seed_path = Path("api/app/scripts/seed_from_movielens.py")

    # Pick top 200 movies by rating count
    item_rating_counts: dict[int, int] = {}
    item_rating_sums: dict[int, float] = {}
    for uid, iid, r in zip(all_user_ids, all_item_ids, all_ratings):
        iid = int(iid)
        item_rating_counts[iid] = item_rating_counts.get(iid, 0) + 1
        item_rating_sums[iid] = item_rating_sums.get(iid, 0.0) + r

    top_movies = sorted(item_rating_counts.keys(), key=lambda x: -item_rating_counts[x])[:200]
    top_movie_set = set(top_movies)

    # Pick 50 most active users
    user_rating_counts: dict[int, int] = {}
    user_rating_sums: dict[int, float] = {}
    for uid, iid, r in zip(all_user_ids, all_item_ids, all_ratings):
        uid = int(uid)
        user_rating_counts[uid] = user_rating_counts.get(uid, 0) + 1
        user_rating_sums[uid] = user_rating_sums.get(uid, 0.0) + r

    top_users = sorted(user_rating_counts.keys(), key=lambda x: -user_rating_counts[x])[:50]
    top_user_set = set(top_users)

    # Extract year from title
    import re

    def extract_year(title: str) -> int | None:
        match = re.search(r"\((\d{4})\)", title)
        return int(match.group(1)) if match else None

    # Write seed script
    movie_data = []
    for mid in top_movies:
        if mid in movies:
            m = movies[mid]
            count = item_rating_counts[mid]
            avg = round(item_rating_sums[mid] / count, 2)
            year = extract_year(m["title"])
            clean_title = re.sub(r"\s*\(\d{4}\)\s*$", "", m["title"])
            movie_data.append({
                "movie_id": mid,
                "title": clean_title,
                "genres": m["genres"],
                "year": year,
                "avg_rating": avg,
                "rating_count": count,
            })

    user_data = []
    for uid in top_users:
        count = user_rating_counts[uid]
        avg = round(user_rating_sums[uid] / count, 2)
        user_data.append({
            "user_id": uid,
            "rating_count": count,
            "avg_rating": avg,
        })

    # Ratings between top users and top movies
    rating_data = []
    for uid, iid, r in zip(all_user_ids, all_item_ids, all_ratings):
        uid, iid = int(uid), int(iid)
        if uid in top_user_set and iid in top_movie_set:
            rating_data.append({"user_id": uid, "movie_id": iid, "rating": float(r)})

    with open(seed_path, "w") as f:
        f.write(f'''"""Seed database with MovieLens data for real recommendations.

Auto-generated by scripts/train_model.py
Contains {len(movie_data)} movies, {len(user_data)} users, {len(rating_data)} ratings.
"""

import asyncio
import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory, engine

MOVIES = {json_mod.dumps(movie_data, indent=2, ensure_ascii=False)}

USERS = {json_mod.dumps(user_data, indent=2)}

RATINGS = {json_mod.dumps(rating_data[:2000])}


async def seed_movies(session: AsyncSession) -> None:
    for m in MOVIES:
        await session.execute(
            text("""
                INSERT INTO movies (movie_id, title, genres, year, avg_rating, rating_count)
                VALUES (:movie_id, :title, CAST(:genres AS JSON), :year, :avg_rating, :rating_count)
                ON CONFLICT (movie_id) DO UPDATE SET
                    title = EXCLUDED.title, genres = CAST(EXCLUDED.genres AS JSON),
                    avg_rating = EXCLUDED.avg_rating, rating_count = EXCLUDED.rating_count
            """),
            {{**m, "genres": json.dumps(m["genres"])}},
        )
    print(f"  Seeded {{len(MOVIES)}} movies")


async def seed_users(session: AsyncSession) -> None:
    for u in USERS:
        await session.execute(
            text("""
                INSERT INTO users (user_id, username, rating_count, avg_rating)
                VALUES (:user_id, :username, :rating_count, :avg_rating)
                ON CONFLICT (user_id) DO UPDATE SET
                    rating_count = EXCLUDED.rating_count, avg_rating = EXCLUDED.avg_rating
            """),
            {{**u, "username": f"user_{{u[\'user_id\']}}"}},
        )
    print(f"  Seeded {{len(USERS)}} users")


async def seed_ratings(session: AsyncSession) -> None:
    for r in RATINGS:
        await session.execute(
            text("""
                INSERT INTO ratings (user_id, movie_id, rating)
                VALUES (:user_id, :movie_id, :rating)
                ON CONFLICT ON CONSTRAINT uq_user_movie_rating DO UPDATE SET
                    rating = EXCLUDED.rating
            """),
            r,
        )
    print(f"  Seeded {{len(RATINGS)}} ratings")


async def main() -> None:
    print("=" * 60)
    print("Seeding Database with MovieLens Data")
    print("=" * 60)

    async with async_session_factory() as session:
        await seed_movies(session)
        await seed_users(session)
        await seed_ratings(session)
        await session.commit()

    await engine.dispose()
    print("\\nDatabase seeded successfully!")


if __name__ == "__main__":
    asyncio.run(main())
''')

    print(f"  Generated seed script: {seed_path}")
    print(f"  {len(movie_data)} movies, {len(user_data)} users, {len(rating_data)} ratings")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("MovieLens ALS Training Pipeline")
    print("=" * 60)

    # Download
    data_path = download_dataset()

    # Load
    user_ids, item_ids, ratings = load_ratings(data_path)
    movies = load_movies(data_path)

    # Train
    user_factors, item_factors, user_map, item_map, metrics = train_als(
        user_ids, item_ids, ratings
    )

    # Export model
    export_model(user_factors, item_factors, user_map, item_map, metrics, movies)

    # Generate seed script
    generate_seed_sql(data_path, movies, user_map, item_map, user_ids, item_ids, ratings)

    print("\n" + "=" * 60)
    print("Pipeline complete!")
    print(f"  Model: {MODEL_DIR}/")
    print(f"  RMSE: {metrics['rmse']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
