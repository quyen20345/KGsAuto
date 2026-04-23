"""
Stage 3: Entity Resolution Pipeline

Fully automated LLM-based entity resolution using LLM-CER algorithm.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import RunConfig
from ..types import Stage3Result
from ..merging.merge_engine import build_cluster_groups, build_id_remap_from_proposals
from ..evaluation.review_ui_stage3 import write_review_dashboard
from ..merging.rewire import collect_entities, load_kg_files, rewire_graph
from ..preprocessing.normalize import normalize_aliases


def _normalize_canonical_aliases(properties: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(properties)
    if "aliases" in normalized:
        normalized["aliases"] = normalize_aliases(normalized.get("aliases"))
    return normalized





def load_stage2_assignments(config: RunConfig) -> list[dict[str, Any]]:
    """Load Stage 2 cluster assignments."""
    path = config.stage_dir("stage2") / "cluster_assignments.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_stage1_embeddings(config: RunConfig) -> dict[str, list[float]]:
    """
    Load embeddings from Stage 1 vector store.

    Fetches vectors from Qdrant or memory store.
    """
    from ..storage.entity_store_adapter import build_vector_store

    store = build_vector_store(
        backend=config.store_backend,
        collection_name=config.resolve_collection_name(),
        vector_dim=config.embedding_dim,
        qdrant_url=config.qdrant_url,
    )
    items = store.fetch_embeddings()

    # Extract embeddings
    embeddings = {}
    for item in items:
        node_id = item.get("node_id")
        vector = item.get("vector")
        if node_id and vector:
            embeddings[node_id] = vector

    return embeddings


def _build_fallback_clustering(record_set: list[dict]) -> dict:
    """Fallback: each entity in separate group."""
    return {
        "groups": [
            {
                "group_id": f"g{i}",
                "node_ids": [item["node_id"]],
                "reasoning": "Fallback clustering",
            }
            for i, item in enumerate(record_set)
        ],
        "confidence": 0.0,
    }


def merge_properties(base: dict[str, Any], other: dict[str, Any]) -> dict[str, Any]:
    """
    Merge two property dictionaries.

    For lists: union
    For scalars: prefer non-empty values from other
    """
    result = dict(base)
    for key, val in other.items():
        if val is None:
            continue

        existing = result.get(key)
        if existing is None:
            result[key] = val
            continue

        if isinstance(existing, list):
            merged = list(existing)
            if isinstance(val, list):
                for item in val:
                    if item not in merged:
                        merged.append(item)
            elif val not in merged:
                merged.append(val)
            result[key] = merged
        else:
            # Prefer non-empty value
            if val and (not existing or len(str(val)) > len(str(existing))):
                result[key] = val

    return result


def build_draft_without_llm(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Build canonical entity using rule-based merging (no LLM).

    Strategy:
    - Pick first candidate as canonical
    - Merge all labels
    - Merge all properties
    """
    if not candidates:
        return {
            "canonical_id": "unknown",
            "labels": [],
            "merged_properties": {},
            "confidence": 0.0,
        }

    canonical_id = candidates[0]["node_id"]
    all_labels = []
    merged_props = {}

    for candidate in candidates:
        # Merge labels
        for label in candidate.get("labels", []):
            if label not in all_labels:
                all_labels.append(label)

        # Merge properties
        merged_props = merge_properties(merged_props, candidate.get("properties", {}))

    return {
        "canonical_id": canonical_id,
        "labels": all_labels,
        "merged_properties": merged_props,
        "confidence": 0.7,
    }


def run_stage3(config: RunConfig) -> Stage3Result:
    """
    Run Stage 3 with LLM-CER (fully automated).

    Pipeline:
    1. Load Stage 2 clusters and Stage 1 embeddings
    2. For each cluster:
       a. NRS: Build record sets
       b. LLM: Cluster each record set
       c. MDG: Validate clustering
       d. CMR: Merge results across rounds
    3. Synthesize canonical entities
    4. Rewire graph
    """
    # Setup logging
    from ..preprocessing.logger import setup_stage_logger
    stage_dir = config.stage_dir("stage3")
    stage_dir.mkdir(parents=True, exist_ok=True)
    logger = setup_stage_logger("stage3", stage_dir / "stage3.log")

    logger.info("=== Starting Stage 3 ===")
    logger.info(f"Stage 3 directory: {stage_dir}")

    # Initialize 2-Pass LLM Resolver
    logger.info("Initializing 2-Pass LLM Resolver...")
    from ..matching.two_pass_llm import TwoPassLLMResolver

    two_pass_resolver = TwoPassLLMResolver(
        llm_provider=config.llm_provider,
        llm_model=config.llm_model,
        llm_api_key=config.llm_api_key,
        conservative_threshold=config.conservative_merge_threshold,
    )
    logger.info("2-Pass LLM Resolver initialized")

    # Load Stage 2 clusters
    logger.info("Loading Stage 2 clusters...")
    assignments = load_stage2_assignments(config)
    groups = build_cluster_groups(assignments)
    logger.info(f"Loaded {len(groups)} clusters")

    # Load Stage 1 embeddings (reuse)
    logger.info("Loading Stage 1 embeddings...")
    embeddings = _load_stage1_embeddings(config)
    logger.info(f"Loaded {len(embeddings)} embeddings")

    # Load entities
    logger.info("Loading entities from input files...")
    kg_files = load_kg_files(config.input_dir)
    entities = collect_entities(kg_files)
    logger.info(f"Loaded {len(entities)} entities")

    # Process each cluster with 2-Pass LLM
    all_canonical_entities = []
    llm_stats = {"total_calls": 0, "pass1_success": 0, "pass2_success": 0, "fallback": 0}

    logger.info(f"Starting to process {len(groups)} clusters with 2-Pass LLM")

    for cluster_id, node_ids in sorted(groups.items()):
        if cluster_id == "noise":
            continue

        # Get primary type summary for the cluster
        cluster_types = sorted({
            row.get("primary_type", "UNKNOWN")
            for row in assignments
            if row.get("cluster_id") == cluster_id
        })
        ptype = cluster_types[0] if len(cluster_types) == 1 else "MIXED"
        cluster_types_display = ", ".join(cluster_types) if cluster_types else "UNKNOWN"

        # Build cluster items with payload
        cluster_items = []
        for node_id in node_ids:
            payload = entities.get(node_id, {"labels": [], "properties": {}})
            cluster_items.append({
                "node_id": node_id,
                "payload": payload,
            })

        logger.info(
            f"Processing cluster {cluster_id} with {len(cluster_items)} entities "
            f"(types: {cluster_types_display}; llm_type: {ptype})"
        )

        # 2-Pass LLM resolution
        canonical_entities = two_pass_resolver.resolve_cluster(
            cluster_entities=cluster_items,
            embeddings=embeddings,
            entity_type=ptype,
        )

        all_canonical_entities.extend(canonical_entities)

    # Build id_remap and canonical_map from canonical entities
    logger.info("Building ID remap and canonical map...")

    # Regenerate canonical IDs from canonical names to ensure consistency
    logger.info("Regenerating canonical IDs from canonical names...")
    from services.entity_resolution.utils.id_builder import build_canonical_id, ensure_unique_canonical_id

    used_ids = set()
    for canonical_entity in all_canonical_entities:
        old_canonical_id = canonical_entity["canonical_id"]
        canonical_name = canonical_entity.get("properties", {}).get("name", "")

        if not canonical_name:
            # Fallback: keep original ID if no name
            logger.warning(f"No canonical name for {old_canonical_id}, keeping original ID")
            new_canonical_id = old_canonical_id
        else:
            # Generate new ID from canonical name
            new_canonical_id = build_canonical_id(canonical_name)
            new_canonical_id = ensure_unique_canonical_id(new_canonical_id, used_ids)

        used_ids.add(new_canonical_id)

        # Store legacy ID for traceability
        canonical_entity["legacy_canonical_id"] = old_canonical_id
        canonical_entity["canonical_id"] = new_canonical_id

    canonical_map = {}
    canonical_overrides = {}

    for canonical_entity in all_canonical_entities:
        canonical_id = canonical_entity.get("canonical_id")
        merged_from = canonical_entity.get("merged_from", [])
        labels = canonical_entity.get("labels", [])
        properties = _normalize_canonical_aliases(canonical_entity.get("properties", {}))

        # Fallback: merge model_extracted and chunk_id from original entities if LLM missed them
        if len(merged_from) > 1:
            # Collect model_extracted and chunk_id from all merged entities
            all_models = set()
            all_chunks = set()
            for node_id in merged_from:
                entity = entities.get(node_id, {})
                entity_props = entity.get("properties", {})

                models = entity_props.get("model_extracted", [])
                if isinstance(models, list):
                    all_models.update(models)
                elif models:
                    all_models.add(models)

                chunks = entity_props.get("chunk_id", [])
                if isinstance(chunks, list):
                    all_chunks.update(chunks)
                elif chunks:
                    all_chunks.add(chunks)

            # Override if LLM returned empty
            if not properties.get("model_extracted"):
                properties["model_extracted"] = sorted(all_models)
            if not properties.get("chunk_id"):
                properties["chunk_id"] = sorted(all_chunks)

        # Map all merged IDs to canonical ID
        for node_id in merged_from:
            canonical_map[node_id] = canonical_id

        # Store canonical entity properties
        if len(merged_from) > 1:
            # Only store overrides for merged entities
            canonical_overrides[canonical_id] = {
                "labels": labels,
                "properties": properties,
                "merged_ids": [nid for nid in merged_from if nid != canonical_id],
                "legacy_canonical_id": canonical_entity.get("legacy_canonical_id"),
            }

    logger.info(f"ID remap: {len(canonical_map)} mappings")
    logger.info(f"Canonical overrides: {len(canonical_overrides)} entities")

    # Save outputs
    remap_path = stage_dir / "id_remap.json"
    with open(remap_path, "w", encoding="utf-8") as f:
        json.dump(canonical_map, f, ensure_ascii=False, indent=2)

    # Rewire graph
    logger.info("Rewiring graph...")
    output_dir = stage_dir / "output_graph"
    rewrite_stats = rewire_graph(
        config.input_dir,
        output_dir,
        canonical_map,
        canonical_overrides=canonical_overrides,
    )

    # Calculate aggregate deduplication metrics
    total_rels_deduplicated = sum(stat.get("relationships_deduplicated", 0) for stat in rewrite_stats)
    total_duplicate_groups = sum(stat.get("duplicate_groups", 0) for stat in rewrite_stats)
    total_rels_before = sum(stat.get("rels_before", 0) for stat in rewrite_stats)
    total_rels_after = sum(stat.get("rels_after", 0) for stat in rewrite_stats)

    logger.info(f"Relationship deduplication: {total_rels_deduplicated} duplicates removed from {total_duplicate_groups} groups")
    logger.info(f"Relationships: {total_rels_before} -> {total_rels_after} (after deduplication)")

    audit_path = stage_dir / "rewire_audit.json"
    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump({
            "run_id": config.run_id,
            "canonical_entities_total": len(all_canonical_entities),
            "canonical_map_size": len(canonical_map),
            "canonical_overrides_size": len(canonical_overrides),
            "relationships_deduplicated": total_rels_deduplicated,
            "duplicate_relationship_groups": total_duplicate_groups,
            "relationships_before": total_rels_before,
            "relationships_after": total_rels_after,
            "rewrite_stats": rewrite_stats,
        }, f, ensure_ascii=False, indent=2)

    logger.info(f"Stage 3 completed successfully")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"ID remap: {remap_path}")
    logger.info(f"Audit: {audit_path}")

    # Create dummy synthesis_decisions for compatibility
    synthesis_decisions_path = stage_dir / "synthesis_decisions.json"
    with open(synthesis_decisions_path, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)

    return Stage3Result(
        run_id=config.run_id,
        decisions_path=str(synthesis_decisions_path),
        id_remap_path=str(remap_path),
        rewire_audit_path=str(audit_path),
        output_dir=str(output_dir),
    )
