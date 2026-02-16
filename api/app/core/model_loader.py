"""ALS model loader - loads factor matrices for real-time scoring.

The model consists of:
  user_factors.npy  (n_users x rank) - User latent factor matrix
  item_factors.npy  (n_items x rank) - Item latent factor matrix
  user_id_map.npy   (n_users,)       - Maps matrix row index -> original userId
  item_id_map.npy   (n_items,)       - Maps matrix col index -> original movieId
  metadata.json                       - Training metadata (rank, rmse, etc.)

Scoring: predicted_rating(u, i) = dot(user_factors[u], item_factors[i])
"""

import json
from pathlib import Path

import numpy as np
import structlog

logger = structlog.get_logger()


class ALSModel:
    """In-memory ALS model for real-time collaborative filtering inference."""

    def __init__(self) -> None:
        self.user_factors: np.ndarray | None = None
        self.item_factors: np.ndarray | None = None
        self.user_id_to_idx: dict[int, int] = {}
        self.item_id_to_idx: dict[int, int] = {}
        self.idx_to_item_id: dict[int, int] = {}
        self.metadata: dict = {}
        self._loaded = False
        # Precomputed norms for cosine similarity
        self._item_norms: np.ndarray | None = None

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def load(self, model_dir: str) -> None:
        """Load model artifacts from disk."""
        model_path = Path(model_dir)

        if not model_path.exists():
            logger.warning("als_model_not_found", path=model_dir)
            return

        try:
            self.user_factors = np.load(model_path / "user_factors.npy")
            self.item_factors = np.load(model_path / "item_factors.npy")
            user_ids = np.load(model_path / "user_id_map.npy")
            item_ids = np.load(model_path / "item_id_map.npy")

            self.user_id_to_idx = {int(uid): idx for idx, uid in enumerate(user_ids)}
            self.item_id_to_idx = {int(iid): idx for idx, iid in enumerate(item_ids)}
            self.idx_to_item_id = {idx: int(iid) for idx, iid in enumerate(item_ids)}

            # Precompute item factor norms for cosine similarity
            norms = np.linalg.norm(self.item_factors, axis=1, keepdims=True)
            norms[norms == 0] = 1e-10  # Avoid division by zero
            self._item_norms = norms

            metadata_path = model_path / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path) as f:
                    self.metadata = json.load(f)

            self._loaded = True
            logger.info(
                "als_model_loaded",
                users=self.user_factors.shape[0],
                items=self.item_factors.shape[0],
                rank=self.user_factors.shape[1],
                rmse=self.metadata.get("rmse"),
            )
        except Exception as e:
            logger.error("als_model_load_failed", error=str(e))
            self._loaded = False

    def predict_for_user(
        self,
        user_id: int,
        item_ids: list[int] | None = None,
        top_k: int = 20,
        exclude_item_ids: set[int] | None = None,
    ) -> list[tuple[int, float]]:
        """Predict ratings for a user across items.

        Args:
            user_id: Original user ID
            item_ids: Specific items to score (None = all items)
            top_k: Number of top results to return
            exclude_item_ids: Set of item IDs to exclude (e.g. already rated)

        Returns:
            List of (movie_id, predicted_rating) tuples, sorted by score desc.
        """
        if not self._loaded or self.user_factors is None or self.item_factors is None:
            return []

        if user_id not in self.user_id_to_idx:
            return []

        user_idx = self.user_id_to_idx[user_id]
        user_vec = self.user_factors[user_idx]  # (rank,)

        if item_ids is not None:
            # Score specific items
            indices = [self.item_id_to_idx[iid] for iid in item_ids if iid in self.item_id_to_idx]
            if not indices:
                return []
            item_vecs = self.item_factors[indices]  # (n x rank)
            scores = item_vecs @ user_vec  # (n,)
            result_ids = [self.idx_to_item_id[idx] for idx in indices]
        else:
            # Score all items
            scores = self.item_factors @ user_vec  # (n_items,)
            result_ids = [self.idx_to_item_id[i] for i in range(len(scores))]

        # Build (movie_id, score) pairs, filtering excluded items
        exclude = exclude_item_ids or set()
        pairs = [
            (mid, float(score))
            for mid, score in zip(result_ids, scores)
            if mid not in exclude
        ]

        # Sort by score descending, take top_k
        pairs.sort(key=lambda x: -x[1])
        return pairs[:top_k]

    def get_similar_items(
        self,
        movie_id: int,
        top_k: int = 10,
        candidate_ids: set[int] | None = None,
    ) -> list[tuple[int, float]]:
        """Find items most similar to a given item using cosine similarity.

        Args:
            movie_id: Original movie ID
            top_k: Number of similar items to return
            candidate_ids: If provided, only consider these movie IDs

        Returns:
            List of (movie_id, similarity_score) tuples.
        """
        if not self._loaded or self.item_factors is None or self._item_norms is None:
            return []

        if movie_id not in self.item_id_to_idx:
            return []

        item_idx = self.item_id_to_idx[movie_id]
        item_vec = self.item_factors[item_idx]  # (rank,)

        # Cosine similarity: (V @ v) / (||V|| * ||v||)
        dot_products = self.item_factors @ item_vec  # (n_items,)
        similarities = dot_products / (self._item_norms.squeeze() * np.linalg.norm(item_vec) + 1e-10)

        # Build candidate set of indices
        if candidate_ids is not None:
            candidate_indices = [
                self.item_id_to_idx[mid]
                for mid in candidate_ids
                if mid in self.item_id_to_idx and mid != movie_id
            ]
            if not candidate_indices:
                return []
            # Get scores for candidates only
            candidate_sims = [(idx, float(similarities[idx])) for idx in candidate_indices]
            candidate_sims.sort(key=lambda x: -x[1])
            return [
                (self.idx_to_item_id[idx], score)
                for idx, score in candidate_sims[:top_k]
            ]
        else:
            # Get top-k from all items (excluding self)
            top_indices = np.argsort(-similarities)
            results = []
            for idx in top_indices:
                idx = int(idx)
                if idx == item_idx:
                    continue
                mid = self.idx_to_item_id.get(idx)
                if mid is not None:
                    results.append((mid, float(similarities[idx])))
                if len(results) >= top_k:
                    break
            return results

    def has_user(self, user_id: int) -> bool:
        """Check if the model has factors for this user."""
        return user_id in self.user_id_to_idx

    def has_item(self, movie_id: int) -> bool:
        """Check if the model has factors for this item."""
        return movie_id in self.item_id_to_idx


# ─── Singleton instance ──────────────────────────────────────────────────────

als_model = ALSModel()


def load_als_model(model_dir: str) -> ALSModel:
    """Load the global ALS model instance."""
    als_model.load(model_dir)
    return als_model


def get_als_model() -> ALSModel:
    """Get the global ALS model instance."""
    return als_model
