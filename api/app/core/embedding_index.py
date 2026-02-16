"""Semantic movie search using sentence embeddings.

Builds an in-memory index of movie text representations encoded with
a sentence embedding model. Supports natural language queries like
"light hearted comedies" or "dark psychological thriller".

Uses fastembed (ONNX-based) for lightweight, fast encoding.
Supports loading pre-computed embeddings for faster cold starts.
"""

import csv
import json
import time
from pathlib import Path

import numpy as np
import structlog

logger = structlog.get_logger()

# Movie text and embedding storage
_movie_ids: list[int] = []
_movie_texts: list[str] = []
_movie_tags: dict[int, list[str]] = {}
_embeddings: np.ndarray | None = None
_embedding_model = None
_loaded = False

PRE_COMPUTED_PATHS = [
    Path("models/embeddings"),
    Path("/app/models/embeddings"),
]


def _load_tags(data_dir: str) -> dict[int, list[str]]:
    """Load user-submitted tags from MovieLens tags.csv."""
    tags: dict[int, list[str]] = {}
    tags_path = Path(data_dir) / "tags.csv"

    if not tags_path.exists():
        logger.warning("tags_file_not_found", path=str(tags_path))
        return tags

    with open(tags_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            movie_id = int(row["movieId"])
            tag = row["tag"].strip().lower()
            if tag and tag != "in netflix queue":
                if movie_id not in tags:
                    tags[movie_id] = []
                tags[movie_id].append(tag)

    for mid in tags:
        tags[mid] = list(dict.fromkeys(tags[mid]))

    logger.info("tags_loaded", movie_count=len(tags), total_tags=sum(len(t) for t in tags.values()))
    return tags


def _build_movie_text(title: str, genres: list[str], tags: list[str]) -> str:
    """Build a rich text representation for a movie."""
    parts = [title]
    if genres:
        parts.append(", ".join(genres))
    if tags:
        parts.append(", ".join(tags[:15]))
    return " | ".join(parts)


def _find_precomputed() -> Path | None:
    """Check if pre-computed embeddings exist."""
    for p in PRE_COMPUTED_PATHS:
        emb_file = p / "movie_embeddings.npy"
        ids_file = p / "movie_ids.npy"
        texts_file = p / "movie_texts.json"
        if emb_file.exists() and ids_file.exists() and texts_file.exists():
            return p
    return None


async def build_embedding_index(
    data_dir: str = "data/raw/ml-latest-small",
) -> None:
    """Build the embedding index from DB movies + MovieLens tags.

    First tries to load pre-computed embeddings for fast cold starts.
    Falls back to encoding from scratch if pre-computed files are missing.
    """
    global _movie_ids, _movie_texts, _movie_tags, _embeddings, _embedding_model, _loaded

    start = time.monotonic()

    # Load tags (needed for search result display regardless)
    _movie_tags = _load_tags(data_dir)

    # Try loading pre-computed embeddings first
    precomputed_dir = _find_precomputed()
    if precomputed_dir:
        try:
            _embeddings = np.load(precomputed_dir / "movie_embeddings.npy")
            ids_arr = np.load(precomputed_dir / "movie_ids.npy")
            _movie_ids = ids_arr.tolist()
            with open(precomputed_dir / "movie_texts.json") as f:
                _movie_texts = json.load(f)

            # Still need the model for encoding queries at runtime
            from fastembed import TextEmbedding
            _embedding_model = TextEmbedding("BAAI/bge-small-en-v1.5")

            _loaded = True
            elapsed = (time.monotonic() - start) * 1000
            logger.info(
                "embedding_index_loaded_precomputed",
                movies=len(_movie_ids),
                embedding_dim=_embeddings.shape[1],
                elapsed_ms=round(elapsed, 0),
            )
            return
        except Exception as e:
            logger.warning("precomputed_embeddings_load_failed", error=str(e))

    # Fallback: build from scratch using DB + fastembed
    from app.core.database import async_session_factory
    from sqlalchemy import text

    async with async_session_factory() as session:
        result = await session.execute(
            text("SELECT movie_id, title, genres FROM movies ORDER BY movie_id")
        )
        rows = result.fetchall()

    if not rows:
        logger.warning("no_movies_for_embedding_index")
        return

    _movie_ids = []
    _movie_texts = []
    for row in rows:
        movie_id, title, genres = row[0], row[1], row[2]
        if isinstance(genres, str):
            genres = json.loads(genres)
        tags = _movie_tags.get(movie_id, [])
        text_repr = _build_movie_text(title, genres or [], tags)
        _movie_ids.append(movie_id)
        _movie_texts.append(text_repr)

    logger.info("movie_texts_built", count=len(_movie_texts))

    try:
        from fastembed import TextEmbedding

        _embedding_model = TextEmbedding("BAAI/bge-small-en-v1.5")

        embeddings_list = list(_embedding_model.embed(_movie_texts))
        _embeddings = np.array(embeddings_list, dtype=np.float32)

        norms = np.linalg.norm(_embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1e-10
        _embeddings = _embeddings / norms

        _loaded = True
        elapsed = (time.monotonic() - start) * 1000
        logger.info(
            "embedding_index_built",
            movies=len(_movie_ids),
            embedding_dim=_embeddings.shape[1],
            elapsed_ms=round(elapsed, 0),
        )
    except Exception as e:
        logger.error("embedding_index_failed", error=str(e))
        _loaded = False


def search_by_description(
    query: str,
    top_k: int = 20,
) -> list[tuple[int, float, str]]:
    """Search movies by natural language description."""
    if not _loaded or _embeddings is None or _embedding_model is None:
        return []

    query_embedding = list(_embedding_model.embed([query]))[0]
    query_embedding = np.array(query_embedding, dtype=np.float32)

    norm = np.linalg.norm(query_embedding)
    if norm > 0:
        query_embedding = query_embedding / norm

    similarities = _embeddings @ query_embedding
    top_indices = np.argsort(-similarities)[:top_k]

    results = []
    for idx in top_indices:
        idx = int(idx)
        results.append((
            _movie_ids[idx],
            float(similarities[idx]),
            _movie_texts[idx],
        ))

    return results


def get_movie_tags(movie_id: int) -> list[str]:
    """Get tags for a specific movie."""
    return _movie_tags.get(movie_id, [])


def is_loaded() -> bool:
    """Check if the embedding index is ready."""
    return _loaded
