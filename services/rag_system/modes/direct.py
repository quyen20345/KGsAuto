from __future__ import annotations

import time
from services.rag_system.modes.common import (
    base_response,
    empty_evidence,
    response_metadata,
)


def run_direct(pipeline, question: str) -> dict:
    """Run direct prompt completion without any retrieval context."""
    start_time = time.perf_counter()

    try:
        response = pipeline.synthesizer.llm.generate(
            prompt=question,
            system_prompt="Bạn là trợ lý AI trả lời câu hỏi ngắn gọn, súc tích, đi thẳng vào vấn đề bằng tiếng Việt.",
            temperature=pipeline.config.llm_temperature,
        )
        answer_text = response.content.strip() if response.content else ""
        token_usage = response.usage_tokens
        metadata = {"model": response.model, "token_usage": token_usage, "mode": "direct"}
    except Exception as e:
        answer_text = f"Xin lỗi, đã xảy ra lỗi khi xử lý câu hỏi: {str(e)}"
        metadata = {"error": str(e), "mode": "direct"}

    synthesis_time_ms = (time.perf_counter() - start_time) * 1000

    return base_response(
        question=question,
        mode="direct",
        answer_text=answer_text,
        citations=[],
        retrieval_time_ms=0.0,
        synthesis_time_ms=synthesis_time_ms,
        metadata=response_metadata(
            metadata,
            budgets={
                "requested_top_k": None,
                "effective_top_k_markdown": None,
                "effective_top_k_graph": None,
            },
        ),
        evidence=empty_evidence(),
    )
