"""
MDG Validator - Misclustering Detection Guardrail

Implements the MDG validation algorithm from the LLM-CER paper.
Validates LLM clustering outputs using embedding similarity.
"""

from __future__ import annotations

import numpy as np
from typing import Any


class MDGValidator:
    """
    Misclustering Detection Guardrail (MDG) for validating LLM outputs.

    Uses embedding similarity to detect when LLM has made clustering errors:
    - High intra-cluster similarity = good (entities in same cluster are similar)
    - Low inter-cluster similarity = good (entities in different clusters are different)
    - If inter-cluster similarity > intra-cluster similarity - threshold → INVALID
    """

    def __init__(
        self,
        similarity_threshold: float = 0.1,
        max_regenerations: int = 3,
    ):
        """
        Initialize MDGValidator.

        Args:
            similarity_threshold: Threshold for MDG check (default: 0.1 from paper)
            max_regenerations: Maximum number of regeneration attempts
        """
        self.similarity_threshold = similarity_threshold
        self.max_regenerations = max_regenerations

    def validate_clustering(
        self,
        clustering_result: dict,
        embeddings: dict[str, list[float]],
    ) -> tuple[bool, str]:
        """
        Validate clustering using MDG algorithm.

        Algorithm:
        1. Compute average intra-cluster similarity (within groups)
        2. Compute average inter-cluster similarity (between groups)
        3. Check: if inter > intra - threshold → INVALID

        Args:
            clustering_result: LLM clustering result with groups
            embeddings: Dictionary mapping node_id to embedding vector

        Returns:
            Tuple of (is_valid, reason)
        """
        groups = clustering_result.get("groups", [])

        # Single group or empty: always valid
        if len(groups) <= 1:
            return True, "Single or empty cluster"

        # Filter out singleton groups for similarity computation
        multi_node_groups = [g for g in groups if len(g.get("node_ids", [])) > 1]

        # If no multi-node groups, check is trivial
        if len(multi_node_groups) == 0:
            return True, "All singleton groups"

        # Compute intra-cluster similarity
        intra_sim = self._compute_intra_similarity(groups, embeddings)

        # Compute inter-cluster similarity
        inter_sim = self._compute_inter_similarity(groups, embeddings)

        # MDG check: inter should be much lower than intra
        # If inter > intra - threshold, clustering is suspicious
        if inter_sim > intra_sim - self.similarity_threshold:
            return False, (
                f"MDG failed: inter_sim={inter_sim:.3f} > "
                f"intra_sim={intra_sim:.3f} - threshold={self.similarity_threshold:.3f}"
            )

        return True, f"MDG passed: intra={intra_sim:.3f}, inter={inter_sim:.3f}"

    def _compute_intra_similarity(
        self,
        groups: list[dict],
        embeddings: dict[str, list[float]],
    ) -> float:
        """
        Compute average intra-cluster similarity.

        For each group with 2+ nodes, compute pairwise similarity
        and average across all pairs in all groups.

        Args:
            groups: List of groups
            embeddings: Node embeddings

        Returns:
            Average intra-cluster similarity
        """
        all_similarities = []

        for group in groups:
            node_ids = group.get("node_ids", [])

            # Skip singleton groups
            if len(node_ids) < 2:
                continue

            # Get embeddings for this group
            vectors = []
            for node_id in node_ids:
                if node_id in embeddings:
                    vectors.append(embeddings[node_id])

            if len(vectors) < 2:
                continue

            # Compute pairwise similarities
            vectors_array = np.array(vectors)
            similarities = self._pairwise_cosine_similarity(vectors_array)

            # Extract upper triangle (avoid diagonal and duplicates)
            n = len(vectors)
            for i in range(n):
                for j in range(i + 1, n):
                    all_similarities.append(similarities[i, j])

        # Return average
        if not all_similarities:
            return 1.0  # No pairs to compare, assume high similarity

        return float(np.mean(all_similarities))

    def _compute_inter_similarity(
        self,
        groups: list[dict],
        embeddings: dict[str, list[float]],
    ) -> float:
        """
        Compute average inter-cluster similarity.

        For each pair of groups, compute average similarity between
        all pairs of nodes from different groups.

        Args:
            groups: List of groups
            embeddings: Node embeddings

        Returns:
            Average inter-cluster similarity
        """
        all_similarities = []

        # Compare each pair of groups
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                group_a = groups[i]
                group_b = groups[j]

                # Get node IDs
                node_ids_a = group_a.get("node_ids", [])
                node_ids_b = group_b.get("node_ids", [])

                # Get embeddings
                vectors_a = [embeddings[nid] for nid in node_ids_a if nid in embeddings]
                vectors_b = [embeddings[nid] for nid in node_ids_b if nid in embeddings]

                if not vectors_a or not vectors_b:
                    continue

                # Compute cross-group similarities
                vectors_a_array = np.array(vectors_a)
                vectors_b_array = np.array(vectors_b)

                # Cosine similarity between all pairs
                for vec_a in vectors_a_array:
                    for vec_b in vectors_b_array:
                        sim = self._cosine_similarity(vec_a, vec_b)
                        all_similarities.append(sim)

        # Return average
        if not all_similarities:
            return 0.0  # No pairs to compare, assume low similarity

        return float(np.mean(all_similarities))

    def _pairwise_cosine_similarity(self, vectors: np.ndarray) -> np.ndarray:
        """
        Compute pairwise cosine similarity matrix.

        Args:
            vectors: Array of shape (n, d) where n is number of vectors

        Returns:
            Similarity matrix of shape (n, n)
        """
        # Normalize vectors
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)  # Avoid division by zero
        normalized = vectors / norms

        # Compute dot product (cosine similarity for normalized vectors)
        similarity_matrix = np.dot(normalized, normalized.T)

        return similarity_matrix

    def _cosine_similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """
        Compute cosine similarity between two vectors.

        Args:
            vec_a: First vector
            vec_b: Second vector

        Returns:
            Cosine similarity (0.0 to 1.0)
        """
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))
