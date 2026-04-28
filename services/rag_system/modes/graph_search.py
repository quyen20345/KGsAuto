from __future__ import annotations

from typing import Optional

from services.rag_system.modes.common import base_response, empty_evidence, run_async
from services.rag_system.retrieval.adapters.neo4j_adapter import Neo4jAdapter
from services.rag_system.workflows.deep_graph_search import pipeline as graph_search_pipeline


def run_graph_search(pipeline, question: str, top_k: Optional[int], include_evidence: bool) -> dict:
    result = run_async(_run_graph_search_reasoning(pipeline, question, top_k))
    return graph_search_response(question, result, include_evidence)


async def arun_graph_search(pipeline, question: str, top_k: Optional[int], include_evidence: bool) -> dict:
    result = await _run_graph_search_reasoning(pipeline, question, top_k)
    return graph_search_response(question, result, include_evidence)


async def _run_graph_search_reasoning(pipeline, question: str, top_k: Optional[int]) -> dict:
    graph_top_k = top_k or pipeline.config.top_k_graph
    return await graph_search_pipeline.graph_search_reasoning(question, Neo4jAdapter(top_k=graph_top_k))


def graph_search_response(question: str, result: dict, include_evidence: bool) -> dict:
    evidence = empty_evidence()
    evidence["graph_context"] = result.get("evidence")

    return base_response(
        question=question,
        mode="graph_search",
        answer_text=result.get("answer", ""),
        citations=result.get("citations", []),
        retrieval_time_ms=result.get("retrieval_time_ms"),
        synthesis_time_ms=result.get("synthesis_time_ms"),
        metadata=result.get("metadata", {}) or {},
        evidence=evidence if include_evidence else None,
        reasoning_steps=result.get("reasoning_steps"),
    )
