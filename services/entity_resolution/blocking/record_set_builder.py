"""
Record Set Builder - NRS Algorithm Implementation

Implements the Next Record Set (NRS) creation algorithm from the LLM-CER paper.
Splits large clusters into optimal record sets for LLM processing.
"""

from __future__ import annotations

import numpy as np
from typing import Any


class RecordSetBuilder:
    """
    Build optimal record sets from clusters using NRS algorithm.

    The algorithm ensures:
    1. Small clusters (≤ optimal_set_size) remain as single sets
    2. Large clusters are split into diverse, balanced sets
    3. Each set has size close to optimal_set_size (default: 9)
    """

    def __init__(
        self,
        optimal_set_size: int = 9,
        target_diversity: int = 4,
        max_variation: float = 0.3,
    ):
        """
        Initialize RecordSetBuilder.

        Args:
            optimal_set_size: Target size for each record set (default: 9 from paper)
            target_diversity: Number of diverse groups to create (default: 4)
            max_variation: Maximum allowed size variation (default: 0.3 = 30%)
        """
        self.optimal_set_size = optimal_set_size
        self.target_diversity = target_diversity
        self.max_variation = max_variation

    def build_record_sets(
        self,
        cluster_items: list[dict],
        embeddings: dict[str, list[float]],
    ) -> list[list[dict]]:
        """
        Build optimal record sets from cluster.

        Algorithm:
        1. If cluster ≤ optimal_set_size: return single set
        2. Else: K-means cluster into target_diversity groups
        3. Sample evenly from each group
        4. Balance set sizes

        Args:
            cluster_items: List of entity items in cluster
            embeddings: Dictionary mapping node_id to embedding vector

        Returns:
            List of record sets, where each set is a list of entity items
        """
        n = len(cluster_items)

        # Small cluster: return as single set
        if n <= self.optimal_set_size:
            return [cluster_items]

        # Large cluster: split into multiple sets
        return self._split_large_cluster(cluster_items, embeddings)

    def _split_large_cluster(
        self,
        cluster_items: list[dict],
        embeddings: dict[str, list[float]],
    ) -> list[list[dict]]:
        """
        Split large cluster into multiple diverse record sets.

        Args:
            cluster_items: List of entity items
            embeddings: Dictionary mapping node_id to embedding vector

        Returns:
            List of record sets
        """
        n = len(cluster_items)

        # Calculate number of sets needed
        num_sets = max(2, (n + self.optimal_set_size - 1) // self.optimal_set_size)

        # Extract embeddings for clustering
        node_ids = [item["node_id"] for item in cluster_items]
        vectors = np.array([embeddings[node_id] for node_id in node_ids])

        # K-means clustering for diversity
        try:
            from sklearn.cluster import KMeans

            # Use min(target_diversity, num_sets) clusters
            k = min(self.target_diversity, num_sets, n)
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(vectors)
        except ImportError:
            # Fallback: random assignment if sklearn not available
            labels = np.random.randint(0, min(self.target_diversity, n), size=n)

        # Group items by cluster label
        groups = {}
        for i, label in enumerate(labels):
            if label not in groups:
                groups[label] = []
            groups[label].append(cluster_items[i])

        # Sample evenly from each group to create record sets
        record_sets = self._sample_evenly(list(groups.values()), num_sets)

        # Balance set sizes
        record_sets = self._balance_sets(record_sets)

        return record_sets

    def _sample_evenly(
        self,
        groups: list[list[dict]],
        num_sets: int,
    ) -> list[list[dict]]:
        """
        Sample evenly from each group to create record sets.

        Args:
            groups: List of groups (each group is a list of items)
            num_sets: Number of record sets to create

        Returns:
            List of record sets
        """
        # Initialize empty record sets
        record_sets = [[] for _ in range(num_sets)]

        # Round-robin assignment from each group
        for group in groups:
            for i, item in enumerate(group):
                set_idx = i % num_sets
                record_sets[set_idx].append(item)

        return record_sets

    def _balance_sets(
        self,
        record_sets: list[list[dict]],
    ) -> list[list[dict]]:
        """
        Balance set sizes to minimize variation.

        Moves items from larger sets to smaller sets to achieve
        more uniform sizes.

        Args:
            record_sets: List of record sets

        Returns:
            Balanced record sets
        """
        if len(record_sets) <= 1:
            return record_sets

        # Calculate target size
        total_items = sum(len(s) for s in record_sets)
        target_size = total_items / len(record_sets)

        # Sort sets by size
        sorted_sets = sorted(enumerate(record_sets), key=lambda x: len(x[1]))

        # Balance: move items from large to small sets
        max_iterations = 10
        for _ in range(max_iterations):
            # Get smallest and largest sets
            small_idx, small_set = sorted_sets[0]
            large_idx, large_set = sorted_sets[-1]

            # Check if balanced enough
            size_diff = len(large_set) - len(small_set)
            if size_diff <= 1:
                break

            # Check variation constraint
            variation = (len(large_set) - target_size) / target_size
            if variation <= self.max_variation:
                break

            # Move one item from large to small
            if len(large_set) > 1:
                item = large_set.pop()
                small_set.append(item)

            # Re-sort
            sorted_sets = sorted(sorted_sets, key=lambda x: len(x[1]))

        # Return original order
        result = [None] * len(record_sets)
        for idx, record_set in sorted_sets:
            result[idx] = record_set

        return result
