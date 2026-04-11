"""
Hierarchical Cluster Merger - CMR Algorithm

Implements the Cluster Merge (CMR) algorithm from the LLM-CER paper.
Merges clustering results across multiple rounds hierarchically.
"""

from __future__ import annotations

import numpy as np
from typing import Any


class HierarchicalClusterMerger:
    """
    Hierarchical Cluster Merger (CMR) for merging results across rounds.

    When a large cluster is split into multiple record sets and processed
    separately, this merges the results back together by finding similar
    groups across rounds.
    """

    def __init__(self, merge_threshold: float = 0.80):
        """
        Initialize HierarchicalClusterMerger.

        Args:
            merge_threshold: Similarity threshold for merging groups (default: 0.80)
        """
        self.merge_threshold = merge_threshold

    def merge_clusters(
        self,
        round_results: list[dict],
        embeddings: dict[str, list[float]],
    ) -> list[dict]:
        """
        Merge clustering results using CMR algorithm.

        Algorithm:
        1. Collect all groups from all rounds
        2. Build similarity matrix between groups
        3. Greedy merge: merge most similar groups first
        4. Respect anti-transitivity (if A merges with B, and B with C, then A merges with C)

        Args:
            round_results: List of clustering results from different rounds
            embeddings: Dictionary mapping node_id to embedding vector

        Returns:
            Final merged clusters (list of groups)
        """
        # Collect all groups from all rounds
        all_groups = []
        for round_idx, result in enumerate(round_results):
            groups = result.get("groups", [])
            for group in groups:
                # Add round info for tracking
                group_copy = dict(group)
                group_copy["round_idx"] = round_idx
                all_groups.append(group_copy)

        # Single round or no groups: no merge needed
        if len(round_results) <= 1 or len(all_groups) <= 1:
            return all_groups

        # Build similarity matrix between groups
        sim_matrix = self._build_similarity_matrix(all_groups, embeddings)

        # Greedy merge
        merged_groups = self._greedy_merge(all_groups, sim_matrix)

        return merged_groups

    def _build_similarity_matrix(
        self,
        groups: list[dict],
        embeddings: dict[str, list[float]],
    ) -> np.ndarray:
        """
        Build pairwise similarity matrix between groups.

        Similarity between two groups = average cosine similarity
        between all pairs of nodes from the two groups.

        Args:
            groups: List of groups
            embeddings: Node embeddings

        Returns:
            Similarity matrix of shape (n_groups, n_groups)
        """
        n = len(groups)
        sim_matrix = np.zeros((n, n))

        for i in range(n):
            for j in range(i + 1, n):
                sim = self._compute_group_similarity(
                    groups[i],
                    groups[j],
                    embeddings,
                )
                sim_matrix[i, j] = sim
                sim_matrix[j, i] = sim

        # Diagonal = 1.0 (self-similarity)
        np.fill_diagonal(sim_matrix, 1.0)

        return sim_matrix

    def _compute_group_similarity(
        self,
        group_a: dict,
        group_b: dict,
        embeddings: dict[str, list[float]],
    ) -> float:
        """
        Compute similarity between two groups.

        Args:
            group_a: First group
            group_b: Second group
            embeddings: Node embeddings

        Returns:
            Average similarity between all pairs of nodes
        """
        node_ids_a = group_a.get("node_ids", [])
        node_ids_b = group_b.get("node_ids", [])

        # Get embeddings
        vectors_a = [embeddings[nid] for nid in node_ids_a if nid in embeddings]
        vectors_b = [embeddings[nid] for nid in node_ids_b if nid in embeddings]

        if not vectors_a or not vectors_b:
            return 0.0

        # Compute average similarity between all pairs
        similarities = []
        for vec_a in vectors_a:
            for vec_b in vectors_b:
                sim = self._cosine_similarity(
                    np.array(vec_a),
                    np.array(vec_b),
                )
                similarities.append(sim)

        return float(np.mean(similarities)) if similarities else 0.0

    def _greedy_merge(
        self,
        groups: list[dict],
        sim_matrix: np.ndarray,
    ) -> list[dict]:
        """
        Greedy merge algorithm.

        Iteratively merge the most similar groups until no more
        merges are possible (all similarities below threshold).

        Args:
            groups: List of groups
            sim_matrix: Similarity matrix

        Returns:
            Merged groups
        """
        n = len(groups)

        # Initialize: each group in its own cluster
        cluster_assignments = list(range(n))  # cluster_assignments[i] = cluster ID for group i

        # Track which groups have been merged
        active = set(range(n))

        while True:
            # Find most similar pair among active groups
            max_sim = -1.0
            best_i, best_j = -1, -1

            for i in active:
                for j in active:
                    if i >= j:
                        continue

                    # Only merge if from different clusters
                    if cluster_assignments[i] == cluster_assignments[j]:
                        continue

                    sim = sim_matrix[i, j]
                    if sim > max_sim:
                        max_sim = sim
                        best_i, best_j = i, j

            # Stop if no pair above threshold
            if max_sim < self.merge_threshold:
                break

            # Merge: assign all groups in cluster j to cluster i
            old_cluster = cluster_assignments[best_j]
            new_cluster = cluster_assignments[best_i]

            for k in range(n):
                if cluster_assignments[k] == old_cluster:
                    cluster_assignments[k] = new_cluster

        # Build final merged groups
        cluster_to_groups = {}
        for i, cluster_id in enumerate(cluster_assignments):
            if cluster_id not in cluster_to_groups:
                cluster_to_groups[cluster_id] = []
            cluster_to_groups[cluster_id].append(groups[i])

        # Merge node_ids within each cluster
        merged_groups = []
        for cluster_id, cluster_groups in cluster_to_groups.items():
            # Collect all node_ids
            all_node_ids = []
            seen = set()
            for group in cluster_groups:
                for node_id in group.get("node_ids", []):
                    if node_id not in seen:
                        all_node_ids.append(node_id)
                        seen.add(node_id)

            # Create merged group
            merged_group = {
                "group_id": f"merged_{cluster_id}",
                "node_ids": all_node_ids,
                "reasoning": f"Merged from {len(cluster_groups)} groups",
                "source_groups": [g.get("group_id") for g in cluster_groups],
            }

            merged_groups.append(merged_group)

        return merged_groups

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
