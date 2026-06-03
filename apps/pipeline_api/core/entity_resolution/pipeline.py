from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from concurrent.futures import Future
from pathlib import Path
from typing import Any, Awaitable, Callable

from apps.pipeline_api.config import ER_ARTIFACTS_DIR
from apps.pipeline_api.core.entity_resolution.blocking.vector_fetch import (
    apply_blocking,
    fetch_incremental_candidates,
)
from apps.pipeline_api.core.entity_resolution.clustering.cluster import cluster_embeddings
from apps.pipeline_api.core.entity_resolution.config import ERConfig, IncrementalERResult
from apps.pipeline_api.core.entity_resolution.matching.two_pass_llm import TwoPassLLMResolver
from apps.pipeline_api.core.entity_resolution.merging.rewire import rewire_graph_neo4j
from apps.pipeline_api.core.entity_resolution.preprocessing.loader import (
    extract_node_records,
    extract_relationship_records,
    load_kg_files,
)
from apps.pipeline_api.core.entity_resolution.preprocessing.normalize import (
    build_embedding_text,
    normalize_aliases,
    normalize_properties,
    primary_type,
)
from apps.pipeline_api.core.entity_resolution.storage.neo4j_store import Neo4jVectorStore
from apps.pipeline_api.core.entity_resolution.types import NodeRecord
from apps.pipeline_api.core.entity_resolution.utils.canonical_name_selector import select_canonical_name
from apps.pipeline_api.core.entity_resolution.utils.id_builder import build_canonical_id, ensure_unique_canonical_id

ProgressEvent = dict[str, Any]
AsyncProgressCallback = Callable[[ProgressEvent], Awaitable[None]]
SyncProgressCallback = Callable[[ProgressEvent], None]
CancelCallback = Callable[[], bool]


def _check_cancel(should_cancel: CancelCallback | None) -> None:
    if should_cancel and should_cancel():
        raise asyncio.CancelledError("Cancelled by user")


def _emit(progress_callback: SyncProgressCallback | None, step: str, progress_pct: int, message: str, **extra: Any) -> None:
    if progress_callback is None:
        return
    progress_callback({
        "step": step,
        "progress_pct": max(0, min(100, int(progress_pct))),
        "message": message,
        **extra,
    })


def _embed_new_records(
    records: list[NodeRecord],
    *,
    run_id: str,
    neo4j_vector_service,
    progress_callback: SyncProgressCallback | None,
) -> list[dict[str, Any]]:
    embedded: list[dict[str, Any]] = []
    total = len(records)
    for idx, rec in enumerate(records, start=1):
        props = normalize_properties(rec.properties)
        text = build_embedding_text(rec.labels, props)
        vector = neo4j_vector_service.embed_text(text)
        payload = {
            "run_id": run_id,
            "node_id": rec.node_id,
            "labels": rec.labels,
            "primary_type": primary_type(rec.labels),
            "source_file": rec.source_file,
            "chunk_id": props.get("chunk_id"),
            "embedding_text": text,
            "properties": props,
            "is_existing": False,
        }
        embedded.append({"node_id": rec.node_id, "vector": vector, "payload": payload})
        if total and (idx == total or idx % 25 == 0):
            _emit(
                progress_callback,
                "embedding",
                5 + round(15 * idx / total),
                f"Embedded {idx}/{total} new entities",
                processed=idx,
                total=total,
            )
    return embedded


def _merge_property_values(existing: Any, incoming: Any) -> Any:
    if existing in (None, "", []):
        return incoming
    if incoming in (None, "", []):
        return existing
    if isinstance(existing, list) or isinstance(incoming, list):
        values = existing if isinstance(existing, list) else [existing]
        more = incoming if isinstance(incoming, list) else [incoming]
        merged = list(values)
        for item in more:
            if item not in merged:
                merged.append(item)
        return merged
    if len(str(incoming)) > len(str(existing)):
        return incoming
    return existing


def _rule_based_canonical(entity_ids: list[str], items_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    labels: list[str] = []
    props: dict[str, Any] = {}
    name_candidates: list[str] = []
    preferred_names: list[str] = []

    for node_id in entity_ids:
        payload = dict(items_by_id[node_id].get("payload") or {})
        for label in payload.get("labels") or []:
            if label not in labels:
                labels.append(label)
        entity_props = dict(payload.get("properties") or {})
        name = entity_props.get("name")
        if name:
            names = name if isinstance(name, list) else [name]
            name_candidates.extend(str(item) for item in names if item)
            preferred_names.extend(str(item) for item in names if item)
        aliases = entity_props.get("aliases") or []
        alias_list = aliases if isinstance(aliases, list) else [aliases]
        name_candidates.extend(str(item) for item in alias_list if item)
        for key, value in entity_props.items():
            props[key] = _merge_property_values(props.get(key), value)

    canonical_name = select_canonical_name(name_candidates, preferred_names)
    if canonical_name:
        props["name"] = canonical_name
    if "aliases" in props:
        props["aliases"] = normalize_aliases(props.get("aliases"))
    return {
        "canonical_id": build_canonical_id(canonical_name or entity_ids[0]),
        "labels": labels,
        "properties": props,
        "merged_from": list(entity_ids),
    }


def _keep_singleton(node_id: str, items_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    payload = dict(items_by_id[node_id].get("payload") or {})
    return {
        "canonical_id": node_id,
        "labels": list(payload.get("labels") or []),
        "properties": dict(payload.get("properties") or {}),
        "merged_from": [node_id],
    }


def _align_canonical_entity(
    canonical: dict[str, Any],
    *,
    existing_ids: set[str],
    used_ids: set[str],
) -> dict[str, Any]:
    aligned = dict(canonical)
    merged_from = [str(node_id) for node_id in aligned.get("merged_from", []) if node_id]
    existing_members = [node_id for node_id in merged_from if node_id in existing_ids]

    if existing_members:
        canonical_id = existing_members[0]
    else:
        props = dict(aligned.get("properties") or {})
        canonical_name = props.get("name") or aligned.get("canonical_id") or (merged_from[0] if merged_from else "unknown")
        canonical_id = build_canonical_id(str(canonical_name))
        if canonical_id not in merged_from:
            canonical_id = ensure_unique_canonical_id(canonical_id, used_ids)

    used_ids.add(canonical_id)
    aligned["canonical_id"] = canonical_id
    aligned["merged_from"] = merged_from or [canonical_id]
    props = dict(aligned.get("properties") or {})
    if "aliases" in props:
        props["aliases"] = normalize_aliases(props.get("aliases"))
    aligned["properties"] = props
    return aligned


def _build_groups(assignments, new_ids: set[str]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    assigned_new: set[str] = set()
    for assignment in assignments:
        if assignment.cluster_id == "noise":
            continue
        groups[assignment.cluster_id].append(assignment.node_id)
        if assignment.node_id in new_ids:
            assigned_new.add(assignment.node_id)

    for node_id in sorted(new_ids - assigned_new):
        groups[f"singleton_{node_id}"] = [node_id]
    return groups


def _resolve_groups(
    groups: dict[str, list[str]],
    items_by_id: dict[str, dict[str, Any]],
    existing_ids: set[str],
    config: ERConfig,
    progress_callback: SyncProgressCallback | None,
) -> tuple[list[dict[str, Any]], int]:
    resolver = TwoPassLLMResolver(
        llm_provider=config.llm_provider,
        llm_model=config.llm_model,
        llm_api_key=config.llm_api_key,
        conservative_threshold=config.conservative_merge_threshold,
    )
    embeddings = {node_id: item.get("vector") or [] for node_id, item in items_by_id.items()}
    canonical_entities: list[dict[str, Any]] = []
    processed = 0

    for idx, (cluster_id, node_ids) in enumerate(sorted(groups.items()), start=1):
        if not any(node_id not in existing_ids for node_id in node_ids):
            continue
        processed += 1
        cluster_items = [{"node_id": node_id, "payload": items_by_id[node_id].get("payload") or {}} for node_id in node_ids]
        cluster_types = sorted({str(items_by_id[node_id].get("payload", {}).get("primary_type", "UNKNOWN")) for node_id in node_ids})
        entity_type = cluster_types[0] if len(cluster_types) == 1 else "MIXED"

        if len(node_ids) == 1:
            resolved = [_keep_singleton(node_ids[0], items_by_id)]
        elif config.enable_llm_blocking:
            try:
                resolved = resolver.resolve_cluster(cluster_items, embeddings, entity_type=entity_type)
            except Exception:
                resolved = [_rule_based_canonical(node_ids, items_by_id)]
        else:
            resolved = [_rule_based_canonical(node_ids, items_by_id)]

        canonical_entities.extend(resolved)
        _emit(
            progress_callback,
            "resolution",
            55 + round(20 * idx / max(len(groups), 1)),
            f"Resolved cluster {cluster_id}",
            cluster_id=cluster_id,
            cluster_size=len(node_ids),
        )
    return canonical_entities, processed


def _build_canonical_outputs(
    canonical_entities: list[dict[str, Any]],
    items_by_id: dict[str, dict[str, Any]],
    existing_ids: set[str],
    neo4j_vector_service,
) -> tuple[dict[str, str], dict[str, dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    used_ids: set[str] = set(existing_ids)
    canonical_map: dict[str, str] = {}
    canonical_overrides: dict[str, dict[str, Any]] = {}
    embedding_items: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []

    for canonical in canonical_entities:
        aligned = _align_canonical_entity(canonical, existing_ids=existing_ids, used_ids=used_ids)
        canonical_id = aligned["canonical_id"]
        merged_from = aligned.get("merged_from") or [canonical_id]
        labels = list(aligned.get("labels") or [])
        props = dict(aligned.get("properties") or {})
        for node_id in merged_from:
            canonical_map[str(node_id)] = canonical_id
        canonical_overrides[canonical_id] = {
            "labels": labels,
            "properties": props,
            "merged_ids": [node_id for node_id in merged_from if node_id != canonical_id],
        }
        embedding_text = neo4j_vector_service.build_entity_embedding_text(labels, props)
        embedding_items.append({
            "node_id": canonical_id,
            "vector": neo4j_vector_service.embed_text(embedding_text),
            "payload": {
                "node_id": canonical_id,
                "labels": labels,
                "primary_type": primary_type(labels),
                "properties": {**props, "embedding_text": embedding_text},
            },
        })
        decisions.append({
            "canonical_id": canonical_id,
            "canonical_name": props.get("name"),
            "merged_from": merged_from,
            "merge_count": len(merged_from),
            "labels": labels,
        })

    # Ensure every new singleton that bypassed a resolver still maps to itself.
    for node_id, item in items_by_id.items():
        if item.get("payload", {}).get("is_existing"):
            continue
        canonical_map.setdefault(node_id, node_id)
    return canonical_map, canonical_overrides, embedding_items, decisions


def _run_incremental_sync(
    *,
    input_dir: Path,
    neo4j_driver,
    neo4j_vector_service,
    config: ERConfig,
    progress_callback: SyncProgressCallback | None,
    should_cancel: CancelCallback | None,
) -> IncrementalERResult:
    _check_cancel(should_cancel)
    audit_dir = config.artifacts_dir / config.run_id / "incremental_er"
    audit_dir.mkdir(parents=True, exist_ok=True)

    _emit(progress_callback, "embedding", 0, "Loading extracted KG files")
    kg_files = load_kg_files(input_dir)
    records = extract_node_records(kg_files)
    relationships = extract_relationship_records(kg_files)

    _check_cancel(should_cancel)
    new_embeddings = _embed_new_records(
        records,
        run_id=config.run_id,
        neo4j_vector_service=neo4j_vector_service,
        progress_callback=progress_callback,
    )

    _check_cancel(should_cancel)
    _emit(progress_callback, "candidate_retrieval", 25, "Searching existing Neo4j candidates")
    neo4j_store = Neo4jVectorStore(neo4j_vector_service)
    combined_items, candidate_map = fetch_incremental_candidates(
        neo4j_store,
        records,
        new_embeddings,
        top_k=config.candidate_top_k,
        min_score=config.candidate_min_score,
    )
    new_ids = {item["node_id"] for item in new_embeddings}
    existing_ids = {item["node_id"] for item in combined_items if item.get("payload", {}).get("is_existing")}

    _check_cancel(should_cancel)
    _emit(progress_callback, "clustering", 45, "Blocking and clustering candidate set")
    blocks = apply_blocking(
        combined_items,
        use_llm_blocking=config.enable_llm_blocking,
        llm_provider=config.llm_provider,
        llm_model=config.llm_model,
        llm_api_key=config.llm_api_key,
    )
    assignments = cluster_embeddings(
        blocks=blocks,
        min_cluster_size=config.min_cluster_size,
        min_samples=config.min_samples,
        similarity_threshold=config.cluster_similarity_threshold,
    )
    groups = _build_groups(assignments, new_ids)
    items_by_id = {item["node_id"]: item for item in combined_items}

    _check_cancel(should_cancel)
    _emit(progress_callback, "resolution", 55, "Resolving clusters")
    canonical_entities, processed_clusters = _resolve_groups(
        groups,
        items_by_id,
        existing_ids,
        config,
        progress_callback,
    )
    canonical_map, canonical_overrides, embedding_items, decisions = _build_canonical_outputs(
        canonical_entities,
        items_by_id,
        existing_ids,
        neo4j_vector_service,
    )

    _check_cancel(should_cancel)
    _emit(progress_callback, "neo4j_upsert", 82, "Updating Neo4j graph")
    rewire_stats = rewire_graph_neo4j(
        neo4j_driver,
        canonical_map,
        canonical_overrides,
        neo4j_vector_service,
        relationships=relationships,
        embedding_items=embedding_items,
    )

    audit = {
        "run_id": config.run_id,
        "input_dir": str(input_dir),
        "new_records": len(records),
        "candidate_map": candidate_map,
        "clusters_processed": processed_clusters,
        "canonical_decisions": decisions,
        "canonical_map": canonical_map,
        "rewire_stats": rewire_stats,
    }
    audit_path = audit_dir / "incremental_er_audit.json"
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

    merged_entities = sum(1 for row in decisions if row.get("merge_count", 0) > 1)
    result = IncrementalERResult(
        run_id=config.run_id,
        new_entities=sum(1 for row in decisions if row["canonical_id"] not in existing_ids),
        merged_entities=merged_entities,
        total_clusters=processed_clusters,
        nodes_created=rewire_stats.get("nodes_created", 0),
        nodes_updated=rewire_stats.get("nodes_updated", 0),
        relationships_created=rewire_stats.get("relationships_created", 0),
        relationships_rewired=rewire_stats.get("relationships_rewired", 0),
        embeddings_updated=rewire_stats.get("embeddings_updated", 0),
        audit_path=str(audit_path),
    )
    _emit(progress_callback, "neo4j_upsert", 100, "Incremental ER completed", result=result.to_dict())
    return result


async def run_incremental_entity_resolution(
    *,
    input_dir: Path,
    neo4j_driver,
    neo4j_vector_service,
    run_id: str,
    artifacts_dir: Path = ER_ARTIFACTS_DIR,
    progress_callback: AsyncProgressCallback | None = None,
    should_cancel: CancelCallback | None = None,
    embedding_model: str | None = None,
    min_cluster_size: int = 2,
    cluster_similarity_threshold: float = 0.72,
    enable_llm_blocking: bool = True,
    llm_provider: str | None = None,
    llm_model: str | None = None,
    candidate_top_k: int = 5,
    candidate_min_score: float = 0.85,
) -> IncrementalERResult:
    config = ERConfig(
        input_dir=input_dir,
        artifacts_dir=artifacts_dir,
        run_id=run_id,
        embedding_model=embedding_model or neo4j_vector_service.embedding_model,
        embedding_dim=neo4j_vector_service.vector_dim,
        min_cluster_size=min_cluster_size,
        cluster_similarity_threshold=cluster_similarity_threshold,
        enable_llm_blocking=enable_llm_blocking,
        llm_provider=llm_provider or ERConfig.llm_provider,
        llm_model=llm_model or ERConfig.llm_model,
        candidate_top_k=candidate_top_k,
        candidate_min_score=candidate_min_score,
    )

    loop = asyncio.get_running_loop()
    pending_callbacks: list[Future] = []

    def emit_progress(event: ProgressEvent) -> None:
        if progress_callback is None:
            return
        pending_callbacks.append(asyncio.run_coroutine_threadsafe(progress_callback(event), loop))

    result = await asyncio.to_thread(
        _run_incremental_sync,
        input_dir=input_dir,
        neo4j_driver=neo4j_driver,
        neo4j_vector_service=neo4j_vector_service,
        config=config,
        progress_callback=emit_progress,
        should_cancel=should_cancel,
    )

    for future in pending_callbacks:
        await asyncio.wrap_future(future)

    return result
