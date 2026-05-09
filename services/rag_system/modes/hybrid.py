from __future__ import annotations

import asyncio
import time
from typing import Any, Optional

from services.rag_system.modes.common import base_response, empty_evidence, markdown_evidence, run_async
from services.rag_system.modes.graph_search import _run_graph_search_reasoning


HYBRID_STRATEGY = "semantic_search_plus_deep_graph_search"


def run_hybrid(pipeline, question: str, top_k: Optional[int], include_evidence: bool) -> dict:
    result = run_async(_run_hybrid(pipeline, question, top_k))
    return hybrid_response(question, result, include_evidence)


async def arun_hybrid(pipeline, question: str, top_k: Optional[int], include_evidence: bool) -> dict:
    result = await _run_hybrid(pipeline, question, top_k)
    return hybrid_response(question, result, include_evidence)


async def _run_hybrid(pipeline, question: str, top_k: Optional[int]) -> dict[str, Any]:
    markdown_top_k = top_k or pipeline.config.top_k_markdown
    graph_top_k = top_k or pipeline.config.top_k_graph

    retrieval_start = time.perf_counter()
    markdown_task = asyncio.to_thread(pipeline.markdown_retriever.retrieve, question, markdown_top_k)
    graph_task = _run_graph_search_reasoning(pipeline, question, top_k)
    markdown_chunks, graph_result = await asyncio.gather(markdown_task, graph_task)
    retrieval_time_ms = (time.perf_counter() - retrieval_start) * 1000

    synthesis_start = time.perf_counter()
    answer = pipeline.synthesizer.synthesize_hybrid_graphsearch(
        question=question,
        markdown_chunks=markdown_chunks,
        graph_context=graph_result.get("evidence"),
        graph_answer=graph_result.get("answer", ""),
        graph_reasoning=graph_result.get("reasoning_steps"),
    )
    synthesis_time_ms = (time.perf_counter() - synthesis_start) * 1000

    return {
        "answer": answer,
        "markdown_chunks": markdown_chunks,
        "graph_result": graph_result,
        "markdown_top_k": markdown_top_k,
        "graph_top_k": graph_top_k,
        "retrieval_time_ms": retrieval_time_ms,
        "synthesis_time_ms": synthesis_time_ms,
    }


def hybrid_response(question: str, result: dict[str, Any], include_evidence: bool) -> dict[str, Any]:
    answer = result["answer"]
    graph_result = result.get("graph_result", {}) or {}

    evidence = empty_evidence()
    evidence["markdown_chunks"] = markdown_evidence(result.get("markdown_chunks", []))
    evidence["graph_context"] = graph_result.get("evidence")
    evidence["graph_reasoning"] = graph_result.get("reasoning_steps")

    retrieved_evidence = {
        "markdown_chunks": evidence["markdown_chunks"],
        "graph_retrieval": graph_result.get("retrieved_evidence"),
    }
    derived_evidence = {
        "graph_derived": graph_result.get("derived_evidence", {}) or {},
    }

    metadata = answer.metadata | {
        "hybrid_strategy": HYBRID_STRATEGY,
        "top_k_markdown": result.get("markdown_top_k"),
        "top_k_graph": result.get("graph_top_k"),
        "graph_metadata": graph_result.get("metadata", {}) or {},
    }

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
