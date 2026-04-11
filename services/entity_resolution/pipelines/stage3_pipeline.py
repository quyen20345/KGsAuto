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
from ..clustering.cluster_merger import HierarchicalClusterMerger
from ..matching.llm_cer import LLMClusterer
from ..evaluation.mdg_validator import MDGValidator
from ..merging.merge_engine import build_cluster_groups, build_id_remap_from_proposals
from ..blocking.record_set_builder import RecordSetBuilder
from ..evaluation.review_ui_stage3 import write_review_dashboard
from ..merging.rewire import collect_entities, load_kg_files, rewire_graph


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
    from ..blocking.vector_fetch import fetch_stage_vectors

    # Fetch vectors from store
    items = fetch_stage_vectors(config)

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
    # Setup
    stage_dir = config.stage_dir("stage3")
    stage_dir.mkdir(parents=True, exist_ok=True)

    # Initialize LLM-CER components
    record_set_builder = RecordSetBuilder(
        optimal_set_size=config.llm_set_size,
        target_diversity=config.llm_diversity,
        max_variation=config.llm_max_variation,
    )

    llm_clusterer = LLMClusterer(
        llm_provider=config.llm_provider,
        llm_model=config.llm_model,
        llm_api_key=config.llm_api_key,
    )

    mdg_validator = MDGValidator(
        similarity_threshold=config.mdg_similarity_threshold,
        max_regenerations=config.mdg_max_regenerations,
    )

    cluster_merger = HierarchicalClusterMerger(
        merge_threshold=config.cmr_merge_threshold,
    )

    # Load Stage 2 clusters
    assignments = load_stage2_assignments(config)
    groups = build_cluster_groups(assignments)

    # Load Stage 1 embeddings (reuse)
    embeddings = _load_stage1_embeddings(config)

    # Load entities
    kg_files = load_kg_files(config.input_dir)
    entities = collect_entities(kg_files)

    # Process each cluster
    all_final_clusters = []
    llm_stats = {"total_calls": 0, "total_tokens": 0, "total_cost": 0.0}

    # Prepare data for review dashboard
    cluster_items_for_ui = []
    cluster_decisions_for_ui = []

    for cluster_id, node_ids in sorted(groups.items()):
        if cluster_id == "noise":
            continue

        # Get primary type
        ptype = "UNKNOWN"
        for row in assignments:
            if row.get("cluster_id") == cluster_id:
                ptype = row.get("primary_type", "UNKNOWN")
                break

        # Build cluster items with payload
        cluster_items = []
        for node_id in node_ids:
            payload = entities.get(node_id, {"labels": [], "properties": {}})
            cluster_items.append({
                "node_id": node_id,
                "payload": payload,
            })

        print(f"Processing cluster {cluster_id} with {len(cluster_items)} entities (type: {ptype})")

        # Step 1: NRS - Build record sets
        record_sets = record_set_builder.build_record_sets(cluster_items, embeddings)
        print(f"  Created {len(record_sets)} record sets")

        # Step 2 & 3: LLM clustering + MDG validation
        round_results = []

        for i, record_set in enumerate(record_sets):
            print(f"  Processing record set {i+1}/{len(record_sets)} ({len(record_set)} entities)")

            # Try up to max_regenerations times
            for attempt in range(config.mdg_max_regenerations):
                try:
                    # LLM clustering
                    clustering_result = llm_clusterer.cluster_record_set(record_set, ptype)
                    llm_stats["total_calls"] += 1

                    # MDG validation
                    is_valid, reason = mdg_validator.validate_clustering(
                        clustering_result,
                        embeddings,
                    )

                    if is_valid:
                        round_results.append(clustering_result)
                        print(f"    MDG passed: {len(clustering_result['groups'])} groups")
                        break
                    else:
                        print(f"    MDG rejected: {reason}, attempt {attempt+1}/{config.mdg_max_regenerations}")

                except Exception as e:
                    print(f"    LLM clustering failed: {e}")
                    if attempt == config.mdg_max_regenerations - 1:
                        # Fallback
                        print(f"    Using fallback clustering")
                        round_results.append(_build_fallback_clustering(record_set))
            else:
                # All attempts failed, use fallback
                print(f"    All MDG attempts failed, using fallback")
                round_results.append(_build_fallback_clustering(record_set))

        # Step 4: CMR - Hierarchical merge
        if len(round_results) > 1:
            print(f"  Merging {len(round_results)} round results")
            merged_clusters = cluster_merger.merge_clusters(round_results, embeddings)
        else:
            merged_clusters = round_results[0]["groups"] if round_results else []

        print(f"  Final: {len(merged_clusters)} clusters")

        # Add cluster_id to each group
        for group in merged_clusters:
            group["original_cluster_id"] = cluster_id
            group["primary_type"] = ptype

        all_final_clusters.extend(merged_clusters)

        # Prepare cluster item for UI
        cluster_candidates = []
        for node_id in node_ids:
            payload = entities.get(node_id, {"labels": [], "properties": {}})
            cluster_candidates.append({
                "node_id": node_id,
                "labels": payload.get("labels", []),
                "properties": payload.get("properties", {}),
            })

        cluster_items_for_ui.append({
            "cluster_id": cluster_id,
            "primary_type": ptype,
            "node_ids": node_ids,
            "candidates": cluster_candidates,
            "cluster_hint": {
                "decision": "MERGE",
                "confidence": 0.8,
                "reasoning": f"LLM-CER processed {len(record_sets)} record sets, produced {len(merged_clusters)} final clusters",
                "suggestion_source": "llm_cer",
                "risk_flags": [],
                "split_groups": [],
            }
        })

        cluster_decisions_for_ui.append({
            "cluster_id": cluster_id,
            "decision": "MERGE",
            "approved": True,
            "split_groups": [],
        })

    # Step 5: Canonical entity synthesis
    print("Synthesizing canonical entities...")
    synthesis_decisions = []
    synthesis_items_for_ui = []
    singleton_skip_total = 0
    merge_decision_total = 0

    for cluster in all_final_clusters:
        node_ids = cluster.get("node_ids", [])

        # Build candidates
        candidates = []
        for node_id in node_ids:
            payload = entities.get(node_id, {"labels": [], "properties": {}})
            candidates.append({
                "node_id": node_id,
                "labels": payload.get("labels", []),
                "properties": payload.get("properties", {}),
            })

        # Use rule-based synthesis (can be replaced with LLM later)
        canonical_entity = build_draft_without_llm(candidates)

        is_singleton = len(node_ids) <= 1
        decision = "SKIP_SINGLETON" if is_singleton else "MERGE"
        approved = not is_singleton
        if is_singleton:
            singleton_skip_total += 1
        else:
            merge_decision_total += 1

        synthesis_decisions.append({
            "proposal_id": cluster.get("group_id", "unknown"),
            "cluster_id": cluster.get("original_cluster_id", "unknown"),
            "decision": decision,
            "canonical_id": canonical_entity.get("canonical_id"),
            "canonical_entity": {
                "labels": canonical_entity.get("labels", []),
                "merged_properties": canonical_entity.get("merged_properties", {}),
            },
            "node_ids": node_ids,
            "by": "llm_cer",
            "confidence": canonical_entity.get("confidence", 0.7),
            "approved": approved,
        })

        # Prepare synthesis item for UI
        synthesis_items_for_ui.append({
            "proposal_id": cluster.get("group_id", "unknown"),
            "cluster_id": cluster.get("original_cluster_id", "unknown"),
            "primary_type": cluster.get("primary_type", "UNKNOWN"),
            "node_ids": node_ids,
            "candidates": candidates,
            "llm_suggestion": {
                "canonical_id": canonical_entity.get("canonical_id"),
                "labels": canonical_entity.get("labels", []),
                "merged_properties": canonical_entity.get("merged_properties", {}),
                "confidence": canonical_entity.get("confidence", 0.7),
                "reasoning": cluster.get("reasoning", "Rule-based synthesis"),
                "suggestion_source": "llm_cer",
                "risk_flags": [],
            }
        })

    # Build approved proposals
    approved_proposals = []
    for d in synthesis_decisions:
        if d.get("decision") == "MERGE" and d.get("approved") and len(d.get("node_ids", [])) > 1:
            approved_proposals.append({
                "proposal_id": d["proposal_id"],
                "cluster_id": d["cluster_id"],
                "node_ids": d["node_ids"],
                "canonical_id": d.get("canonical_id"),
            })

    # Step 6: Graph rewiring
    print("Rewiring graph...")
    canonical_map = build_id_remap_from_proposals(approved_proposals)

    # Build canonical overrides
    canonical_overrides = {}
    for d in synthesis_decisions:
        if d.get("decision") != "MERGE" or not d.get("approved"):
            continue

        canonical_id = d.get("canonical_id")
        if not canonical_id:
            continue

        ce = d.get("canonical_entity", {})
        props = ce.get("merged_properties", {})
        labels = ce.get("labels", [])

        prev = canonical_overrides.get(canonical_id)
        if prev:
            prev["properties"] = merge_properties(prev.get("properties", {}), props)
            for lbl in labels:
                if lbl not in prev["labels"]:
                    prev["labels"].append(lbl)
            for node_id in d["node_ids"]:
                if node_id != canonical_id and node_id not in prev["merged_ids"]:
                    prev["merged_ids"].append(node_id)
        else:
            canonical_overrides[canonical_id] = {
                "labels": list(labels),
                "properties": dict(props),
                "merged_ids": [node_id for node_id in d["node_ids"] if node_id != canonical_id],
            }

    # Save outputs
    synthesis_decisions_path = stage_dir / "synthesis_decisions.json"
    with open(synthesis_decisions_path, "w", encoding="utf-8") as f:
        json.dump(synthesis_decisions, f, ensure_ascii=False, indent=2)

    remap_path = stage_dir / "id_remap.json"
    with open(remap_path, "w", encoding="utf-8") as f:
        json.dump(canonical_map, f, ensure_ascii=False, indent=2)

    output_dir = stage_dir / "output_graph"
    rewrite_stats = rewire_graph(
        config.input_dir,
        output_dir,
        canonical_map,
        canonical_overrides=canonical_overrides,
    )

    audit_path = stage_dir / "rewire_audit.json"
    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump({
            "run_id": config.run_id,
            "synthesis_decisions_total": len(synthesis_decisions),
            "canonical_map_size": len(canonical_map),
                "rewrite_stats": rewrite_stats,
                "llm_stats": llm_stats,
                "merge_decisions_total": merge_decision_total,
                "singleton_skips_total": singleton_skip_total,
                "effective_merges_total": len(canonical_map),
            }, f, ensure_ascii=False, indent=2)

    # Generate review dashboard
    print("Generating review dashboard...")
    synthesis_decisions_for_ui = [
        {
            "proposal_id": d["proposal_id"],
            "cluster_id": d["cluster_id"],
            "decision": d["decision"],
            "approved": d["approved"],
        }
        for d in synthesis_decisions
    ]

    dashboard_path = write_review_dashboard(
        stage_dir,
        cluster_items_for_ui,
        cluster_decisions_for_ui,
        synthesis_items_for_ui,
        synthesis_decisions_for_ui,
    )
    print(f"Review dashboard: {dashboard_path}")

    print(f"LLM-CER Stats: {llm_stats['total_calls']} calls")

    return Stage3Result(
        run_id=config.run_id,
        decisions_path=str(synthesis_decisions_path),
        id_remap_path=str(remap_path),
        rewire_audit_path=str(audit_path),
        output_dir=str(output_dir),
    )
