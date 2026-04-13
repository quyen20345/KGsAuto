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
from ..blocking.vector_fetch import fetch_stage_vectors
from ..clustering.cluster import cluster_embeddings
from ..evaluation.metrics import calculate_cluster_metrics
from ..evaluation.review_ui_stage2 import write_cluster_dashboard


def run_stage2(config: RunConfig) -> Stage2Result:
    # Setup logging
    logger = setup_stage_logger("stage2", config.stage_dir("stage2") / "stage2.log")
    logger.info(f"Starting Stage 2: run_id={config.run_id}")

    # Fetch vectors from store (blocking module)
    logger.info(f"Fetching vectors from store: collection={config.resolve_collection_name()}")
    items = fetch_stage_vectors(config)
    logger.info(f"Fetched {len(items)} vectors from store")

    # Log clustering parameters
    logger.info(
        f"Clustering parameters: min_cluster_size={config.min_cluster_size}, "
        f"min_samples={config.min_samples}, "
        f"similarity_threshold={config.cluster_similarity_threshold}, "
        f"by_primary_type={config.cluster_by_primary_type}"
    )

    # Perform clustering
    assignments = cluster_embeddings(
        items=items,
        min_cluster_size=config.min_cluster_size,
        min_samples=config.min_samples,
        similarity_threshold=config.cluster_similarity_threshold,
        by_primary_type=config.cluster_by_primary_type,
    )

    # Fuzzy matching validation (PERSON only)
    if config.enable_fuzzy_validation_person:
        logger.info("Validating PERSON clusters with fuzzy matching...")
        from ..matching.fuzzy_validation import (
            validate_person_cluster,
            split_person_cluster_by_similarity,
        )

        # Group by cluster
        clusters = defaultdict(list)
        for a in assignments:
            if a.cluster_id != "noise":
                # Find corresponding item
                item = next(x for x in items if x["node_id"] == a.node_id)
                clusters[a.cluster_id].append(item)

        # Validate and split clusters (PERSON fuzzy validation only)
        validated_assignments = []
        person_split_count = 0

        # Initialize cluster_counter with max existing IDs for each type
        cluster_counter = defaultdict(int)
        for cluster_id in clusters.keys():
            # Extract type and number from cluster_id (e.g., "person_0042" -> "PERSON", 42)
            parts = cluster_id.rsplit("_", 1)
            if len(parts) == 2 and parts[1].isdigit():
                type_key = parts[0]
                cluster_num = int(parts[1])
                # Find the primary_type for this cluster
                cluster_items = clusters[cluster_id]
                if cluster_items:
                    ptype = cluster_items[0]["payload"]["primary_type"]
                    cluster_counter[ptype] = max(cluster_counter[ptype], cluster_num + 1)

        for cluster_id, cluster_items in clusters.items():
            ptype = cluster_items[0]["payload"]["primary_type"]

            # REMOVED: Source constraint validation
            # Let Stage 3 (2-Pass LLM) handle entities from same source

            # Check PERSON-specific fuzzy validation
            if ptype == "PERSON":
                # Check fuzzy similarity for PERSON
                fuzzy_valid, fuzzy_reason = validate_person_cluster(
                    cluster_items,
                    min_name_similarity=config.min_name_similarity,
                    min_alias_similarity=config.min_alias_similarity,
                )

                if fuzzy_valid:
                    # Valid PERSON cluster, keep as is
                    for item in cluster_items:
                        orig = next(a for a in assignments if a.node_id == item["node_id"])
                        validated_assignments.append(orig)
                else:
                    # Invalid PERSON cluster, split by similarity
                    logger.warning(f"PERSON cluster {cluster_id}: {fuzzy_reason}")

                    sub_clusters = split_person_cluster_by_similarity(
                        cluster_items,
                        min_name_similarity=config.min_name_similarity,
                        min_alias_similarity=config.min_alias_similarity,
                    )

                    person_split_count += len(sub_clusters) - 1

                    for sub_cluster in sub_clusters:
                        if len(sub_cluster) >= config.min_cluster_size:
                            new_cluster_id = f"person_{cluster_counter['PERSON']:04d}"
                            cluster_counter['PERSON'] += 1

                            for item in sub_cluster:
                                orig = next(a for a in assignments if a.node_id == item["node_id"])
                                validated_assignments.append(ClusterAssignment(
                                    node_id=orig.node_id,
                                    cluster_id=new_cluster_id,
                                    probability=orig.probability,
                                    primary_type=orig.primary_type,
                                ))
                        else:
                            for item in sub_cluster:
                                validated_assignments.append(ClusterAssignment(
                                    node_id=item["node_id"],
                                    cluster_id="noise",
                                    probability=0.0,
                                    primary_type="PERSON",
                                ))
            else:
                # Non-PERSON types: source already validated, keep as is
                for item in cluster_items:
                    orig = next(a for a in assignments if a.node_id == item["node_id"])
                    validated_assignments.append(orig)

        # Add original noise
        for a in assignments:
            if a.cluster_id == "noise":
                validated_assignments.append(a)

        # Replace assignments with validated ones
        assignments = validated_assignments

        logger.info(f"Validation completed: {person_split_count} PERSON clusters split")
    else:
        logger.info("Fuzzy validation disabled, skipping...")

    # Calculate cluster quality metrics
    logger.info("Calculating cluster quality metrics...")
    metrics = calculate_cluster_metrics(items, assignments)
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
    by_node = {str(x.get("node_id")): x for x in items}
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
                "source_document_id": source_payload.get("source_document_id"),
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
