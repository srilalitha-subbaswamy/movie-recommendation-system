"""Pre-compute movie embeddings for faster cold starts.

Builds text representations from movies.csv + tags.csv,
encodes them with fastembed, and saves the embeddings as .npy files.
The API can load these at startup instead of re-encoding everything.

Usage:
    python scripts/build_embeddings.py

Output:
    models/embeddings/movie_embeddings.npy  - (N, 384) float32 matrix
    models/embeddings/movie_ids.npy         - (N,) int array
    models/embeddings/movie_texts.json      - list of text representations
"""

import csv
import json
import sys
from pathlib import Path

import numpy as np

DATA_PATHS = [
    Path("data/raw/ml-latest-small"),
    Path("/app/data/raw/ml-latest-small"),
]

OUTPUT_DIR_PATHS = [
    Path("models/embeddings"),
    Path("/app/models/embeddings"),
]


def find_data_path() -> Path:
    for p in DATA_PATHS:
        if p.exists() and (p / "movies.csv").exists():
            return p
    print("ERROR: MovieLens data not found")
    sys.exit(1)


def find_output_dir() -> Path:
    for p in OUTPUT_DIR_PATHS:
        if p.parent.exists():
            p.mkdir(parents=True, exist_ok=True)
            return p
    OUTPUT_DIR_PATHS[0].mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR_PATHS[0]


def load_tags(data_path: Path) -> dict[int, list[str]]:
    tags: dict[int, list[str]] = {}
    tags_file = data_path / "tags.csv"
    if not tags_file.exists():
        return tags
    with open(tags_file, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            mid = int(row["movieId"])
            tag = row["tag"].strip().lower()
            if tag and tag != "in netflix queue":
                if mid not in tags:
                    tags[mid] = []
                tags[mid].append(tag)
    for mid in tags:
        tags[mid] = list(dict.fromkeys(tags[mid]))
    return tags


def load_movies(data_path: Path) -> list[tuple[int, str, list[str]]]:
    import re
    movies = []
    with open(data_path / "movies.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            mid = int(row["movieId"])
            title = row["title"]
            title = re.sub(r"\s*\(\d{4}\)\s*$", "", title)
            genres = row["genres"].split("|") if row["genres"] != "(no genres listed)" else []
            movies.append((mid, title, genres))
    return movies


def build_text(title: str, genres: list[str], tags: list[str]) -> str:
    parts = [title]
    if genres:
        parts.append(", ".join(genres))
    if tags:
        parts.append(", ".join(tags[:15]))
    return " | ".join(parts)


def main():
    data_path = find_data_path()
    output_dir = find_output_dir()

    print("=" * 60)
    print("Pre-computing Movie Embeddings")
    print(f"Data: {data_path}")
    print(f"Output: {output_dir}")
    print("=" * 60)

    tags = load_tags(data_path)
    movies = load_movies(data_path)
    print(f"Loaded {len(movies)} movies, {len(tags)} movies with tags")

    movie_ids = []
    movie_texts = []
    for mid, title, genres in movies:
        movie_tags = tags.get(mid, [])
        text = build_text(title, genres, movie_tags)
        movie_ids.append(mid)
        movie_texts.append(text)

    print(f"Built {len(movie_texts)} text representations")
    print("Encoding with fastembed (BAAI/bge-small-en-v1.5)...")

    from fastembed import TextEmbedding
    model = TextEmbedding("BAAI/bge-small-en-v1.5")
    embeddings_list = list(model.embed(movie_texts))
    embeddings = np.array(embeddings_list, dtype=np.float32)

    # Normalize
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1e-10
    embeddings = embeddings / norms

    print(f"Embeddings shape: {embeddings.shape}")

    # Save
    np.save(output_dir / "movie_embeddings.npy", embeddings)
    np.save(output_dir / "movie_ids.npy", np.array(movie_ids, dtype=np.int32))
    with open(output_dir / "movie_texts.json", "w") as f:
        json.dump(movie_texts, f)

    print(f"Saved to {output_dir}/")
    print("=" * 60)


if __name__ == "__main__":
    main()
