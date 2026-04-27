"""Unified retrieval/RAG pipeline for semantic, graph, KG-RAG, and hybrid modes."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Optional

from services.rag_system.config import RAGConfig
from services.rag_system.components.synthesis import AnswerSynthesizer
from services.rag_system.retrieval.graph import GraphRetriever
from services.rag_system.retrieval.hybrid import HybridRetriever
from services.rag_system.retrieval.markdown import MarkdownRetriever
from services.rag_system.schemas import GraphEvidence, MarkdownEvidence


UNIFIED_MODES = {"semantic_search", "graph_search", "naive_grag", "hybrid"}
MODE_ALIASES: dict[str, str] = {}


def canonical_unified_mode(mode: str) -> str:
    canonical = MODE_ALIASES.get(mode.strip().lower(), mode.strip().lower())
    if canonical not in UNIFIED_MODES:
        supported = ", ".join(sorted(UNIFIED_MODES))
        raise ValueError(f"Unsupported unified retrieval mode: {mode}. Supported modes: {supported}")
    return canonical


def _markdown_evidence(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
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


def _graph_evidence(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
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


def _empty_evidence() -> dict[str, Any]:
    return {
        "markdown_chunks": [],
        "graph_facts": [],
        "graph_context": None,
    }


def _run_async(awaitable):
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


class UnifiedRetrievalPipeline:
    """Single orchestration entrypoint for user-facing retrieval/RAG modes."""

    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or RAGConfig()
        self.markdown_retriever = MarkdownRetriever(self.config)
        self.graph_retriever = GraphRetriever(self.config)
        self.hybrid_retriever = HybridRetriever(self.config)
        self.synthesizer = AnswerSynthesizer(self.config)

    def query(
        self,
        question: str,
        mode: str = "semantic_search",
        top_k: Optional[int] = None,
        include_evidence: bool = True,
    ) -> dict[str, Any]:
        start_time = time.perf_counter()
        canonical = canonical_unified_mode(mode)

        if canonical == "semantic_search":
            result = self._query_semantic_search(question, top_k, include_evidence)
        elif canonical == "graph_search":
            result = self._query_graph_search(question, top_k, include_evidence)
        elif canonical == "naive_grag":
            result = self._query_naive_grag(question, top_k, include_evidence)
        else:
            result = self._query_hybrid(question, top_k, include_evidence)

        result["total_time_ms"] = (time.perf_counter() - start_time) * 1000
        return result

    async def aquery(
        self,
        question: str,
        mode: str = "semantic_search",
        top_k: Optional[int] = None,
        include_evidence: bool = True,
    ) -> dict[str, Any]:
        start_time = time.perf_counter()
        canonical = canonical_unified_mode(mode)

        if canonical == "semantic_search":
            result = await asyncio.to_thread(self._query_semantic_search, question, top_k, include_evidence)
        elif canonical == "graph_search":
            result = await self._aquery_graph_search(question, top_k, include_evidence)
        elif canonical == "naive_grag":
            result = await self._aquery_naive_grag(question, top_k, include_evidence)
        else:
            result = await asyncio.to_thread(self._query_hybrid, question, top_k, include_evidence)

        result["total_time_ms"] = (time.perf_counter() - start_time) * 1000
        return result

    def _base_response(
        self,
        question: str,
        mode: str,
        answer_text: str,
        citations: list[str],
        retrieval_time_ms: float | None,
        synthesis_time_ms: float | None,
        metadata: dict[str, Any],
        evidence: dict[str, Any] | None,
        reasoning_steps: Any = None,
    ) -> dict[str, Any]:
        return {
            "question": question,
            "mode": mode,
            "answer": answer_text,
            "citations": citations,
            "evidence": evidence,
            "reasoning_steps": reasoning_steps,
            "retrieval_time_ms": retrieval_time_ms,
            "synthesis_time_ms": synthesis_time_ms,
            "metadata": metadata,
        }

    def _query_semantic_search(self, question: str, top_k: Optional[int], include_evidence: bool) -> dict[str, Any]:
        retrieval_start = time.perf_counter()
        chunks = self.markdown_retriever.retrieve(question, top_k=top_k)
        retrieval_time_ms = (time.perf_counter() - retrieval_start) * 1000

        synthesis_start = time.perf_counter()
        answer = self.synthesizer.synthesize_markdown_only(question, chunks)
        synthesis_time_ms = (time.perf_counter() - synthesis_start) * 1000

        evidence = _empty_evidence()
        evidence["markdown_chunks"] = _markdown_evidence(chunks)

        return self._base_response(
            question=question,
            mode="semantic_search",
            answer_text=answer.text,
            citations=answer.citations,
            retrieval_time_ms=retrieval_time_ms,
            synthesis_time_ms=synthesis_time_ms,
            metadata=answer.metadata,
            evidence=evidence if include_evidence else None,
        )

    def _query_graph_search(self, question: str, top_k: Optional[int], include_evidence: bool) -> dict[str, Any]:
        result = _run_async(self._run_graph_search_reasoning(question, top_k))
        return self._graph_search_response(question, result, include_evidence)

    async def _aquery_graph_search(self, question: str, top_k: Optional[int], include_evidence: bool) -> dict[str, Any]:
        result = await self._run_graph_search_reasoning(question, top_k)
        return self._graph_search_response(question, result, include_evidence)

    async def _run_graph_search_reasoning(self, question: str, top_k: Optional[int]) -> dict[str, Any]:
        from services.rag_system.retrieval.adapters.neo4j_adapter import Neo4jAdapter
        from services.rag_system.workflows.deep_graph_search.pipeline import graph_search_reasoning

        graph_top_k = top_k or self.config.top_k_graph
        return await graph_search_reasoning(question, Neo4jAdapter(top_k=graph_top_k))

    def _graph_search_response(self, question: str, result: dict[str, Any], include_evidence: bool) -> dict[str, Any]:
        evidence = _empty_evidence()
        evidence["graph_context"] = result.get("evidence")

        return self._base_response(
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

    def _query_naive_grag(self, question: str, top_k: Optional[int], include_evidence: bool) -> dict[str, Any]:
        result = _run_async(self._run_naive_grag_reasoning(question, top_k))
        return self._naive_grag_response(question, result, include_evidence)

    async def _aquery_naive_grag(self, question: str, top_k: Optional[int], include_evidence: bool) -> dict[str, Any]:
        result = await self._run_naive_grag_reasoning(question, top_k)
        return self._naive_grag_response(question, result, include_evidence)

    async def _run_naive_grag_reasoning(self, question: str, top_k: Optional[int]) -> dict[str, Any]:
        from services.rag_system.retrieval.adapters.neo4j_adapter import Neo4jAdapter
        from services.rag_system.workflows.deep_graph_search.pipeline import naive_grag_reasoning

        graph_top_k = top_k or self.config.top_k_graph
        return await naive_grag_reasoning(question, Neo4jAdapter(top_k=graph_top_k))

    def _naive_grag_response(self, question: str, result: dict[str, Any], include_evidence: bool) -> dict[str, Any]:
        evidence = _empty_evidence()
        evidence["graph_context"] = result.get("context")

        return self._base_response(
            question=question,
            mode="naive_grag",
            answer_text=result.get("answer", ""),
            citations=result.get("citations", []),
            retrieval_time_ms=result.get("retrieval_time_ms"),
            synthesis_time_ms=result.get("synthesis_time_ms"),
            metadata=result.get("metadata", {}) or {},
            evidence=evidence if include_evidence else None,
        )

    def _query_hybrid(self, question: str, top_k: Optional[int], include_evidence: bool) -> dict[str, Any]:
        retrieval_start = time.perf_counter()
        retrieved = self.hybrid_retriever.retrieve(
            question,
            top_k_markdown=top_k or self.config.top_k_markdown,
            top_k_graph=top_k or self.config.top_k_graph,
        )
        retrieval_time_ms = (time.perf_counter() - retrieval_start) * 1000

        markdown_chunks = retrieved["markdown_chunks"]
        graph_facts = retrieved["graph_facts"]

        synthesis_start = time.perf_counter()
        answer = self.synthesizer.synthesize_hybrid(question, markdown_chunks, graph_facts)
        synthesis_time_ms = (time.perf_counter() - synthesis_start) * 1000

        evidence = _empty_evidence()
        evidence["markdown_chunks"] = _markdown_evidence(markdown_chunks)
        evidence["graph_facts"] = _graph_evidence(graph_facts)
        evidence["merged_context"] = retrieved.get("merged_context")

        fusion_metadata = {
            "fusion_strategy": getattr(self.config, "fusion_strategy", "weighted"),
            "markdown_weight": getattr(self.config, "markdown_weight", None),
            "graph_weight": getattr(self.config, "graph_weight", None),
        }

        return self._base_response(
            question=question,
            mode="hybrid",
            answer_text=answer.text,
            citations=answer.citations,
            retrieval_time_ms=retrieval_time_ms,
            synthesis_time_ms=synthesis_time_ms,
            metadata=answer.metadata | fusion_metadata,
            evidence=evidence if include_evidence else None,
        )
