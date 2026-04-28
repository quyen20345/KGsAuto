from __future__ import annotations

import time
from typing import Optional

from services.rag_system.modes.common import base_response, empty_evidence, markdown_evidence


def run_semantic_search(pipeline, question: str, top_k: Optional[int], include_evidence: bool) -> dict:
    retrieval_start = time.perf_counter()
    chunks = pipeline.markdown_retriever.retrieve(question, top_k=top_k)
    retrieval_time_ms = (time.perf_counter() - retrieval_start) * 1000

    synthesis_start = time.perf_counter()
    answer = pipeline.synthesizer.synthesize_markdown_only(question, chunks)
    synthesis_time_ms = (time.perf_counter() - synthesis_start) * 1000

    evidence = empty_evidence()
    evidence["markdown_chunks"] = markdown_evidence(chunks)

    return base_response(
        question=question,
        mode="semantic_search",
        answer_text=answer.text,
        citations=answer.citations,
        retrieval_time_ms=retrieval_time_ms,
        synthesis_time_ms=synthesis_time_ms,
        metadata=answer.metadata,
        evidence=evidence if include_evidence else None,
    )
