from __future__ import annotations

from typing import Optional

from services.rag_system.modes.common import base_response, empty_evidence, run_async
from services.rag_system.graph.neo4j_context_adapter import Neo4jAdapter
from services.rag_system.graph.graph_search import pipeline as graph_search_pipeline


def run_naive_grag(pipeline, question: str, top_k: Optional[int], include_evidence: bool) -> dict:
    result = run_async(_run_naive_grag_reasoning(pipeline, question, top_k))
    return naive_grag_response(question, result, include_evidence)


async def arun_naive_grag(pipeline, question: str, top_k: Optional[int], include_evidence: bool) -> dict:
    result = await _run_naive_grag_reasoning(pipeline, question, top_k)
    return naive_grag_response(question, result, include_evidence)


async def _run_naive_grag_reasoning(pipeline, question: str, top_k: Optional[int]) -> dict:
    graph_top_k = top_k or pipeline.config.top_k_graph
    return await graph_search_pipeline.naive_grag_reasoning(question, Neo4jAdapter(top_k=graph_top_k))


def naive_grag_response(question: str, result: dict, include_evidence: bool) -> dict:
    evidence = empty_evidence()
    evidence["graph_context"] = result.get("context")

    return base_response(
        question=question,
        mode="naive_grag",
        answer_text=result.get("answer", ""),
        citations=result.get("citations", []),
        retrieval_time_ms=result.get("retrieval_time_ms"),
        synthesis_time_ms=result.get("synthesis_time_ms"),
        metadata=result.get("metadata", {}) or {},
        evidence=evidence if include_evidence else None,
    )
