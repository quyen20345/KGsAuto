"""Unified retrieval/RAG pipeline for semantic, graph, KG-RAG, and hybrid modes."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Optional

from services.rag_system.config import RAGConfig
from services.rag_system.synthesis import AnswerSynthesizer
from services.rag_system.modes import (
    arun_graph_search,
    arun_hybrid,
    arun_naive_grag,
    run_graph_search,
    run_hybrid,
    run_naive_grag,
    run_semantic_search,
)
from services.rag_system.retrieval.markdown import MarkdownRetriever


UNIFIED_MODES = {"semantic_search", "graph_search", "naive_grag", "hybrid"}
MODE_ALIASES: dict[str, str] = {}


def canonical_unified_mode(mode: str) -> str:
    canonical = MODE_ALIASES.get(mode.strip().lower(), mode.strip().lower())
    if canonical not in UNIFIED_MODES:
        supported = ", ".join(sorted(UNIFIED_MODES))
        raise ValueError(f"Unsupported unified retrieval mode: {mode}. Supported modes: {supported}")
    return canonical


class UnifiedRetrievalPipeline:
    """Single orchestration entrypoint for user-facing retrieval/RAG modes."""

    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or RAGConfig()
        self.markdown_retriever = MarkdownRetriever(self.config)
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
            result = run_semantic_search(self, question, top_k, include_evidence)
        elif canonical == "graph_search":
            result = run_graph_search(self, question, top_k, include_evidence)
        elif canonical == "naive_grag":
            result = run_naive_grag(self, question, top_k, include_evidence)
        else:
            result = run_hybrid(self, question, top_k, include_evidence)

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
            result = await asyncio.to_thread(run_semantic_search, self, question, top_k, include_evidence)
        elif canonical == "graph_search":
            result = await arun_graph_search(self, question, top_k, include_evidence)
        elif canonical == "naive_grag":
            result = await arun_naive_grag(self, question, top_k, include_evidence)
        else:
            result = await arun_hybrid(self, question, top_k, include_evidence)

        result["total_time_ms"] = (time.perf_counter() - start_time) * 1000
        return result
