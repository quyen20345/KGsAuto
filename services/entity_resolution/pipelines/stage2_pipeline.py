"""
Stage 2 Pipeline: Clustering

Orchestrates blocking, matching, and clustering modules.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict

from ..config import RunConfig
from ..preprocessing.logger import setup_stage_logger
from ..types import ClusterAssignment, Stage2Result
from ..blocking.vector_fetch import fetch_and_block_vectors
from ..clustering.cluster import cluster_embeddings
from ..evaluation.metrics import calculate_cluster_metrics
from ..evaluation.review_ui_stage2 import write_cluster_dashboard


def run_stage2(config: RunConfig) -> Stage2Result:
    # Setup logging
    logger = setup_stage_logger("stage2", config.stage_dir("stage2") / "stage2.log")
    logger.info(f"Starting Stage 2: run_id={config.run_id}")

    # Fetch vectors and apply blocking
    logger.info(f"Fetching vectors and applying blocking strategy (LLM-based: {config.enable_llm_blocking})")
    blocks = fetch_and_block_vectors(config, use_llm_blocking=config.enable_llm_blocking)

    total_items = sum(len(items) for items in blocks.values())
    logger.info(f"Fetched {total_items} vectors from store")
    logger.info("=" * 80)
    logger.info(f"Created {len(blocks)} blocks:")
    for block_id, items in blocks.items():
        unique_label_combinations = sorted({
            tuple(sorted(item.get("payload", {}).get("labels", [])))
            for item in items
        })
        unique_types = sorted({
            label
            for labels in unique_label_combinations
            for label in labels
        })
        logger.info(f"  - {block_id}: {len(items)} entities")
        logger.info(f"    Types: {unique_types}")
        logger.info(f"    Label combinations: {[list(labels) for labels in unique_label_combinations]}")
    logger.info("=" * 80)

    # Log clustering parameters
    logger.info(
        f"Clustering parameters: min_cluster_size={config.min_cluster_size}, "
        f"min_samples={config.min_samples}, "
        f"similarity_threshold={config.cluster_similarity_threshold}"
    )

    # Perform clustering on each block
    assignments = cluster_embeddings(
        blocks=blocks,
        min_cluster_size=config.min_cluster_size,
        min_samples=config.min_samples,
        similarity_threshold=config.cluster_similarity_threshold,
    )

    # Stage 2 responsibility: Blocking + Clustering only
    # All validation is handled by Stage 3 Two-Pass LLM (has full context)
    logger.info("Stage 2 clustering completed. Validation will be handled by Stage 3.")

    # Flatten blocks for metrics calculation
    all_items = [item for block_items in blocks.values() for item in block_items]

    # Calculate cluster quality metrics
    logger.info("Calculating cluster quality metrics...")
    metrics = calculate_cluster_metrics(all_items, assignments)
    sil_score = metrics.get("silhouette_score")
    if sil_score is not None:
        logger.info(f"Silhouette score: {sil_score:.3f}")
    else:
        logger.info("Silhouette score: N/A (not enough clusters or sklearn unavailable)")

    # Log clustering results
    clusters_count = metrics.get("num_clusters", 0)
    noise_count = metrics.get("num_noise", 0)
    logger.info(f"Clustering completed: {clusters_count} clusters, {noise_count} noise points")

    # Save assignments
    stage_dir = config.stage_dir("stage2")
    stage_dir.mkdir(parents=True, exist_ok=True)
    assignments_path = stage_dir / "cluster_assignments.json"

    payload = [
        {
            "node_id": a.node_id,
            "cluster_id": a.cluster_id,
            "probability": a.probability,
            "primary_type": a.primary_type,
        }
        for a in assignments
    ]

    with open(assignments_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved cluster assignments to: {assignments_path}")

    # Enrich with node metadata
    by_node = {str(x.get("node_id")): x for x in all_items}
    enriched = []
    for row in payload:
        source = by_node.get(row["node_id"], {})
        source_payload = dict(source.get("payload", {}))
        props = dict(source_payload.get("properties", {}))
        enriched.append(
            {
                **row,
                "node_name": props.get("name"),
                "labels": source_payload.get("labels", []),
                "source_file": source_payload.get("source_file"),
                "chunk_id": source_payload.get("chunk_id"),
            }
        )

    enriched_path = stage_dir / "cluster_assignments_enriched.json"
    with open(enriched_path, "w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved enriched assignments to: {enriched_path}")

    # Save metrics to JSON
    metrics_path = stage_dir / "cluster_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved cluster metrics to: {metrics_path}")

    # Generate dashboard with metrics
    write_cluster_dashboard(stage_dir, enriched, metrics)
    logger.info(f"Generated cluster dashboard: {stage_dir / 'cluster_dashboard.html'}")

    # Calculate statistics
    cluster_ids = [a.cluster_id for a in assignments if a.cluster_id != "noise"]
    counter = Counter(cluster_ids)

    logger.info(f"Stage 2 completed successfully")

    return Stage2Result(
        run_id=config.run_id,
        collection_name=config.resolve_collection_name(),
        assignments_path=str(assignments_path),
        clusters_total=len(counter),
        noise_total=sum(1 for a in assignments if a.cluster_id == "noise"),
    )
