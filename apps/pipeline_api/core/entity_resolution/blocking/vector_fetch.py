"""Vector fetching helpers for incremental entity resolution."""

from __future__ import annotations

from typing import Any

from .llm_blocking_strategy import LLMBlockingStrategy
from .primary_type_blocking import PrimaryTypeBlockingStrategy


def apply_blocking(
    items: list[dict[str, Any]],
    *,
    use_llm_blocking: bool,
    llm_provider: str | None = None,
    llm_model: str | None = None,
    llm_api_key: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    if not items:
        return {}
    if use_llm_blocking and llm_provider and llm_model:
        try:
            strategy = LLMBlockingStrategy(
                llm_provider=llm_provider,
                llm_model=llm_model,
                llm_api_key=llm_api_key,
            )
            return strategy.block(items)
        except Exception:
            pass
    return PrimaryTypeBlockingStrategy().block(items)


def fetch_and_block_vectors(config, use_llm_blocking: bool = True) -> dict[str, list[dict[str, Any]]]:
    store = getattr(config, "vector_store", None)
    if store is None:
        raise ValueError("config.vector_store is required for apps incremental ER vector fetching")
    items = store.fetch_embeddings()
    return apply_blocking(
        items,
        use_llm_blocking=use_llm_blocking,
        llm_provider=getattr(config, "llm_provider", None),
        llm_model=getattr(config, "llm_model", None),
        llm_api_key=getattr(config, "llm_api_key", None),
    )


def fetch_incremental_candidates(
    neo4j_store,
    new_records: list[Any],
    new_embeddings: list[dict[str, Any]],
    top_k: int = 5,
    min_score: float = 0.85,
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    del new_records
    combined_by_id: dict[str, dict[str, Any]] = {}
    candidate_map: dict[str, list[str]] = {}
    missing_vectors: set[str] = set()

    for item in new_embeddings:
        node_id = str(item.get("node_id") or "")
        if not node_id:
            continue
        combined_by_id[node_id] = item
        hits = neo4j_store.search_similar(
            item.get("vector") or [],
            top_k=top_k,
            min_score=min_score,
        )
        candidate_ids: list[str] = []
        for hit in hits:
            candidate_id = str(hit.get("node_id") or "")
            if not candidate_id or candidate_id == node_id:
                continue
            if candidate_id not in candidate_ids:
                candidate_ids.append(candidate_id)
            if hit.get("vector"):
                payload = dict(hit.get("payload") or {})
                payload["is_existing"] = True
                hit["payload"] = payload
                combined_by_id.setdefault(candidate_id, hit)
            else:
                missing_vectors.add(candidate_id)
        candidate_map[node_id] = candidate_ids

    if missing_vectors and hasattr(neo4j_store, "fetch_embeddings_by_ids"):
        for item in neo4j_store.fetch_embeddings_by_ids(sorted(missing_vectors)):
            combined_by_id.setdefault(str(item.get("node_id")), item)

    return list(combined_by_id.values()), candidate_map
