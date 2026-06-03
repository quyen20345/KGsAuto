from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


def calculate_cluster_metrics(items: list[dict], assignments: list) -> dict[str, Any]:
    """
    Calculate cluster quality metrics.

    Args:
        items: List of items with vectors
        assignments: List of ClusterAssignment objects

    Returns:
        Dictionary with metrics including silhouette_score, cluster counts, sizes
    """
    if not items or not assignments:
        return {
            "silhouette_score": None,
            "num_clusters": 0,
            "num_noise": 0,
            "cluster_sizes": {},
            "avg_cluster_size": 0.0,
            "max_cluster_size": 0,
            "min_cluster_size": 0,
        }

    try:
        from sklearn.metrics import silhouette_score
    except ImportError:
        logger.warning("sklearn not available, silhouette_score will be None")
        silhouette_score = None

    # Extract vectors and labels
    vectors = np.array([x["vector"] for x in items])
    labels = np.array([a.cluster_id for a in assignments])

    # Filter out noise points
    mask = labels != "noise"
    num_non_noise = mask.sum()

    # Calculate cluster size distribution
    from collections import Counter

    cluster_sizes = Counter(labels)
    num_clusters = len([cid for cid in cluster_sizes.keys() if cid != "noise"])
    num_noise = int(cluster_sizes.get("noise", 0))

    # Calculate silhouette score if we have enough clusters
    sil_score = None
    if silhouette_score is not None and num_non_noise >= 2 and num_clusters >= 2:
        try:
            filtered_vectors = vectors[mask]
            filtered_labels = labels[mask]

            # Convert cluster_id strings to integers for sklearn
            unique_labels = list(set(filtered_labels))
            label_map = {cid: idx for idx, cid in enumerate(unique_labels)}
            numeric_labels = np.array([label_map[cid] for cid in filtered_labels])

            # Calculate silhouette score with cosine metric
            sil_score = silhouette_score(filtered_vectors, numeric_labels, metric="cosine")
            logger.info(f"Silhouette score: {sil_score:.3f}")
        except Exception as e:
            logger.warning(f"Failed to calculate silhouette score: {e}")
            sil_score = None

    # Calculate cluster size statistics (excluding noise)
    non_noise_sizes = [v for k, v in cluster_sizes.items() if k != "noise"]
    avg_size = float(np.mean(non_noise_sizes)) if non_noise_sizes else 0.0
    max_size = max(non_noise_sizes, default=0)
    min_size = min(non_noise_sizes, default=0)

    return {
        "silhouette_score": float(sil_score) if sil_score is not None else None,
        "num_clusters": num_clusters,
        "num_noise": num_noise,
        "cluster_sizes": dict(cluster_sizes),
        "avg_cluster_size": avg_size,
        "max_cluster_size": max_size,
        "min_cluster_size": min_size,
    }
