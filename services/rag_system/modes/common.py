from __future__ import annotations

import asyncio
from typing import Any

from services.rag_system.schemas import GraphEvidence, MarkdownEvidence


def markdown_evidence(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence = []
    for chunk in chunks:
        evidence.append(
            MarkdownEvidence(
                chunk_id=chunk.get("chunk_id", ""),
                doc_id=chunk.get("doc_id", ""),
                text=chunk.get("text", ""),
                score=chunk.get("score", 0.0) or 0.0,
                source_path=chunk.get("source_path"),
                title=chunk.get("title"),
                section=chunk.get("section"),
                metadata=chunk.get("metadata", {}) or {},
            ).model_dump()
        )
    return evidence


def graph_evidence(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence = []
    for fact in facts:
        evidence.append(
            GraphEvidence(
                entity_id=fact.get("entity_id", ""),
                entity_name=fact.get("entity_name", ""),
                fact_type=fact.get("fact_type", "property"),
                fact_text=fact.get("fact_text", ""),
                score=fact.get("score", 0.0) or 0.0,
                cypher_query=fact.get("cypher_query"),
                metadata=fact.get("metadata", {}) or {},
            ).model_dump()
        )
    return evidence


def empty_evidence() -> dict[str, Any]:
    return {
        "markdown_chunks": [],
        "graph_facts": [],
        "graph_context": None,
    }


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
