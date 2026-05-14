from __future__ import annotations

import asyncio
import time
from typing import Any, Optional

from services.rag_system.modes.common import (
    base_response,
    effective_budgets,
    empty_evidence,
    pack_markdown_chunks,
    response_metadata,
    run_async,
)
from services.rag_system.modes.graph_search import _run_graph_search_reasoning


HYBRID_STRATEGY = "semantic_search_plus_deep_graph_search"


def run_hybrid(pipeline, question: str, top_k: Optional[int], include_evidence: bool) -> dict:
    result = run_async(_run_hybrid(pipeline, question, top_k))
    return hybrid_response(question, result, include_evidence)


async def arun_hybrid(pipeline, question: str, top_k: Optional[int], include_evidence: bool) -> dict:
    result = await _run_hybrid(pipeline, question, top_k)
    return hybrid_response(question, result, include_evidence)


async def _run_hybrid(pipeline, question: str, top_k: Optional[int]) -> dict[str, Any]:
    budgets = effective_budgets(pipeline.config, "hybrid", top_k)
    markdown_top_k = budgets["effective_top_k_markdown"]
    graph_top_k = budgets["effective_top_k_graph"]

    retrieval_start = time.perf_counter()
    markdown_task = asyncio.to_thread(pipeline.markdown_retriever.retrieve, question, markdown_top_k)
    graph_task = _run_graph_search_reasoning(pipeline, question, graph_top_k)
    markdown_chunks, graph_result = await asyncio.gather(markdown_task, graph_task)
    retrieval_time_ms = (time.perf_counter() - retrieval_start) * 1000

    packed_chunks, markdown_pack_stats = pack_markdown_chunks(markdown_chunks, max_items=markdown_top_k)

    synthesis_start = time.perf_counter()
    answer = pipeline.synthesizer.synthesize_hybrid_graphsearch(
        question=question,
        markdown_chunks=packed_chunks,
        graph_context=graph_result.get("evidence"),
        graph_answer=graph_result.get("answer", ""),
        graph_reasoning=graph_result.get("reasoning_steps"),
    )
    synthesis_time_ms = (time.perf_counter() - synthesis_start) * 1000

    return {
        "answer": answer,
        "markdown_chunks": packed_chunks,
        "raw_markdown_count": len(markdown_chunks),
        "markdown_pack_stats": markdown_pack_stats,
        "graph_result": graph_result,
        "budgets": budgets,
        "retrieval_time_ms": retrieval_time_ms,
        "synthesis_time_ms": synthesis_time_ms,
    }


def hybrid_response(question: str, result: dict[str, Any], include_evidence: bool) -> dict[str, Any]:
    answer = result["answer"]
    graph_result = result.get("graph_result", {}) or {}
    graph_retrieval = graph_result.get("retrieved_evidence")
    markdown_chunks = result.get("markdown_chunks", [])
    markdown_pack_stats = result.get("markdown_pack_stats", {}) or {}

    evidence = empty_evidence()
    evidence["markdown_chunks"] = markdown_chunks
    evidence["graph_context"] = graph_result.get("evidence")
    evidence["graph_reasoning"] = graph_result.get("reasoning_steps")

    retrieved_evidence = {
        "markdown_chunks": markdown_chunks,
        "graph_retrieval": graph_retrieval,
    }
    derived_evidence = {
        "graph_derived": graph_result.get("derived_evidence", {}) or {},
    }

    retrieved_graph_count = len(graph_retrieval) if isinstance(graph_retrieval, list) else None
    metadata = response_metadata(
        answer.metadata,
        result.get("budgets", {}) or {},
        {
            "hybrid_strategy": HYBRID_STRATEGY,
            "retrieved_markdown_count": result.get("raw_markdown_count"),
            "packed_markdown_count": markdown_pack_stats.get("packed_count"),
            "dropped_markdown_count": markdown_pack_stats.get("dropped_count"),
            "retrieved_graph_count": retrieved_graph_count,
            "graph_metadata": graph_result.get("metadata", {}) or {},
        },
    )

    return base_response(
        question=question,
        mode="hybrid",
        answer_text=answer.text,
        citations=answer.citations,
        retrieval_time_ms=result.get("retrieval_time_ms"),
        synthesis_time_ms=result.get("synthesis_time_ms"),
        metadata=metadata,
        evidence=evidence if include_evidence else None,
        reasoning_steps=graph_result.get("reasoning_steps"),
        retrieved_evidence=retrieved_evidence,
        derived_evidence=derived_evidence,
    )
