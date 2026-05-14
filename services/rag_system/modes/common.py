from __future__ import annotations

import asyncio
from typing import Any

from services.rag_system.schemas import GraphEvidence, MarkdownEvidence


def _score(value: Any) -> float:
    return float(value or 0.0)


def normalize_markdown_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence = []
    seen = set()
    for rank, chunk in enumerate(chunks, 1):
        chunk_id = str(chunk.get("chunk_id") or "")
        key = chunk_id or str(chunk.get("text") or "")
        if key in seen:
            continue
        seen.add(key)
        metadata = dict(chunk.get("metadata", {}) or {})
        metadata.setdefault("rank", rank)
        evidence.append(
            MarkdownEvidence(
                chunk_id=chunk_id,
                text=chunk.get("text", ""),
                score=_score(chunk.get("score")),
                section=chunk.get("section"),
                metadata=metadata,
            ).model_dump()
        )
    return evidence


def markdown_evidence(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return normalize_markdown_chunks(chunks)


def normalize_graph_facts(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence = []
    seen = set()
    for rank, fact in enumerate(facts, 1):
        fact_text = str(fact.get("fact_text") or fact.get("description") or fact.get("text") or "")
        entity_id = str(fact.get("entity_id") or fact.get("id") or "")
        entity_name = str(fact.get("entity_name") or fact.get("name") or "")
        fact_type = fact.get("fact_type") or fact.get("type") or "property"
        if fact_type not in {"property", "relation", "path"}:
            fact_type = "property"
        key = (entity_id, entity_name, fact_type, fact_text)
        if key in seen or not fact_text:
            continue
        seen.add(key)
        metadata = dict(fact.get("metadata", {}) or {})
        metadata.setdefault("rank", rank)
        evidence.append(
            GraphEvidence(
                entity_id=entity_id,
                entity_name=entity_name,
                fact_type=fact_type,
                fact_text=fact_text,
                score=_score(fact.get("score")),
                cypher_query=fact.get("cypher_query"),
                metadata=metadata,
            ).model_dump()
        )
    return evidence


def graph_evidence(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return normalize_graph_facts(facts)


def empty_evidence() -> dict[str, Any]:
    return {
        "markdown_chunks": [],
        "graph_facts": [],
        "graph_context": None,
    }


def effective_budgets(config: Any, mode: str, top_k: int | None) -> dict[str, Any]:
    requested_top_k = top_k
    markdown_top_k = top_k if top_k is not None else config.top_k_markdown
    graph_top_k = top_k if top_k is not None else config.top_k_graph
    if mode == "semantic_search":
        graph_top_k = None
    elif mode in {"graph_search", "naive_grag"}:
        markdown_top_k = None
    return {
        "requested_top_k": requested_top_k,
        "effective_top_k_markdown": markdown_top_k,
        "effective_top_k_graph": graph_top_k,
    }


def pack_markdown_chunks(
    chunks: list[dict[str, Any]],
    max_items: int | None = None,
    max_chars: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    normalized = normalize_markdown_chunks(chunks)
    return _pack_items(normalized, "text", max_items, max_chars)


def pack_graph_facts(
    facts: list[dict[str, Any]],
    max_items: int | None = None,
    max_chars: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    normalized = normalize_graph_facts(facts)
    return _pack_items(normalized, "fact_text", max_items, max_chars)


def _pack_items(
    items: list[dict[str, Any]],
    text_key: str,
    max_items: int | None,
    max_chars: int | None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    packed = []
    used_chars = 0
    item_limit = max_items if max_items is not None else len(items)
    char_limit = max_chars if max_chars is not None else sum(len(str(item.get(text_key) or "")) for item in items)

    for item in items:
        if len(packed) >= item_limit:
            break
        text_len = len(str(item.get(text_key) or ""))
        if packed and used_chars + text_len > char_limit:
            break
        packed.append(item)
        used_chars += text_len

    return packed, {
        "input_count": len(items),
        "packed_count": len(packed),
        "dropped_count": max(len(items) - len(packed), 0),
        "packed_chars": used_chars,
    }


def response_metadata(
    metadata: dict[str, Any] | None = None,
    budgets: dict[str, Any] | None = None,
    counts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    merged = dict(metadata or {})
    if budgets:
        merged.update(budgets)
    if counts:
        merged.update(counts)
    return merged


def base_response(
    question: str,
    mode: str,
    answer_text: str,
    citations: list[str],
    retrieval_time_ms: float | None,
    synthesis_time_ms: float | None,
    metadata: dict[str, Any],
    evidence: dict[str, Any] | None,
    reasoning_steps: Any = None,
    retrieved_evidence: Any = None,
    derived_evidence: Any = None,
) -> dict[str, Any]:
    token_usage = metadata.get("token_usage") if isinstance(metadata, dict) else None
    return {
        "question": question,
        "mode": mode,
        "answer": answer_text,
        "citations": citations,
        "evidence": evidence,
        "reasoning_steps": reasoning_steps,
        "retrieved_evidence": retrieved_evidence,
        "derived_evidence": derived_evidence,
        "retrieval_time_ms": retrieval_time_ms,
        "synthesis_time_ms": synthesis_time_ms,
        "token_usage": token_usage,
        "metadata": metadata,
    }


def run_async(awaitable):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    close = getattr(awaitable, "close", None)
    if close:
        close()
    raise RuntimeError(
        "UnifiedRetrievalPipeline.query() cannot run async GraphSearch work inside an active event loop; "
        "use await UnifiedRetrievalPipeline.aquery(...) instead"
    )
