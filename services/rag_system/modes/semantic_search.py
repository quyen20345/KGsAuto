from __future__ import annotations

import time
from typing import Optional

from services.rag_system.modes.common import (
    base_response,
    effective_budgets,
    empty_evidence,
    pack_markdown_chunks,
    response_metadata,
)


def run_semantic_search(pipeline, question: str, top_k: Optional[int], include_evidence: bool) -> dict:
    budgets = effective_budgets(pipeline.config, "semantic_search", top_k)
    markdown_top_k = budgets["effective_top_k_markdown"]

    retrieval_start = time.perf_counter()
    chunks = pipeline.markdown_retriever.retrieve(question, top_k=markdown_top_k)
    retrieval_time_ms = (time.perf_counter() - retrieval_start) * 1000

    packed_chunks, pack_stats = pack_markdown_chunks(chunks, max_items=markdown_top_k)

    synthesis_start = time.perf_counter()
    answer = pipeline.synthesizer.synthesize_markdown_only(question, packed_chunks)
    synthesis_time_ms = (time.perf_counter() - synthesis_start) * 1000

    evidence = empty_evidence()
    evidence["markdown_chunks"] = packed_chunks

    metadata = response_metadata(
        answer.metadata,
        budgets,
        {
            "retrieved_markdown_count": len(chunks),
            "packed_markdown_count": pack_stats["packed_count"],
            "dropped_markdown_count": pack_stats["dropped_count"],
        },
    )

    return base_response(
        question=question,
        mode="semantic_search",
        answer_text=answer.text,
        citations=answer.citations,
        retrieval_time_ms=retrieval_time_ms,
        synthesis_time_ms=synthesis_time_ms,
        metadata=metadata,
        evidence=evidence if include_evidence else None,
        retrieved_evidence={"markdown_chunks": packed_chunks},
    )
