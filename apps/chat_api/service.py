from __future__ import annotations

import json
import time
import uuid
from typing import Any

from services.rag_system import RAGConfig, UnifiedRetrievalPipeline
from services.rag_system.pipeline import UNIFIED_MODES, canonical_unified_mode

from apps.chat_api.schemas import ChatError, ChatQueryRequest, ChatQueryResponse, OpenAIChatCompletionRequest


DEFAULT_MODE = "semantic_search"
SUPPORTED_MODES = tuple(sorted(UNIFIED_MODES))

_pipeline: UnifiedRetrievalPipeline | None = None


def get_pipeline() -> UnifiedRetrievalPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = UnifiedRetrievalPipeline(RAGConfig())
    return _pipeline


def reset_pipeline() -> None:
    """Reset cached pipeline. Intended for tests."""
    global _pipeline
    _pipeline = None


def _metadata_from_result(result: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(result.get("metadata") or {})
    for key in ("retrieval_time_ms", "synthesis_time_ms", "total_time_ms", "reasoning_steps"):
        if key in result and result[key] is not None:
            metadata[key] = result[key]
    return metadata


def normalize_chat_response(req: ChatQueryRequest, result: dict[str, Any]) -> ChatQueryResponse:
    return ChatQueryResponse(
        answer=result.get("answer", ""),
        mode=result.get("mode", req.mode),
        conversation_id=req.conversation_id,
        citations=result.get("citations") or [],
        evidence=result.get("evidence"),
        metadata=_metadata_from_result(result),
        error=None,
    )


async def query_chat(req: ChatQueryRequest) -> ChatQueryResponse:
    mode = canonical_unified_mode(req.mode)
    result = await get_pipeline().aquery(
        question=req.message,
        mode=mode,
        top_k=req.top_k,
        include_evidence=req.include_evidence,
    )
    return normalize_chat_response(req.model_copy(update={"mode": mode}), result)


def _message_content_to_text(content: str | list[dict[str, Any]] | None) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for item in content:
        if item.get("type") == "text" and isinstance(item.get("text"), str):
            parts.append(item["text"])
    return "\n".join(parts).strip()


def openai_request_to_chat_query(req: OpenAIChatCompletionRequest) -> ChatQueryRequest:
    """Map an OpenAI-compatible chat request to KGsAuto's chat query."""

    user_messages = [msg for msg in req.messages if msg.role == "user"]
    if not user_messages:
        raise ValueError("OpenAI-compatible request must include at least one user message")

    message = _message_content_to_text(user_messages[-1].content)
    if not message:
        raise ValueError("Last user message is empty")

    mode = req.mode or req.model or DEFAULT_MODE
    return ChatQueryRequest(
        message=message,
        mode=mode,
        top_k=req.top_k,
        include_evidence=req.include_evidence,
        conversation_id=req.conversation_id,
    )


async def query_openai_compatible(req: OpenAIChatCompletionRequest) -> ChatQueryResponse:
    return await query_chat(openai_request_to_chat_query(req))


def _compact_reasoning_steps(reasoning: Any) -> list[dict[str, Any]]:
    if not reasoning:
        return []
    if isinstance(reasoning, str):
        return [{"title": "Reasoning", "summary": reasoning}]
    if isinstance(reasoning, list):
        return [
            step if isinstance(step, dict) and ("title" in step or "summary" in step) else {"title": f"Bước {index + 1}", "summary": str(step)}
            for index, step in enumerate(reasoning)
        ]
    if not isinstance(reasoning, dict):
        return [{"title": "Reasoning", "summary": str(reasoning)}]

    steps: list[dict[str, Any]] = []
    text_queries = reasoning.get("text_queries") or []
    kg_queries = reasoning.get("kg_queries") or []
    text_expanded = reasoning.get("text_expanded_queries") or []
    kg_expanded = reasoning.get("kg_expanded_queries") or []

    if text_queries or kg_queries:
        parts = []
        if text_queries:
            parts.append(f"{len(text_queries)} truy vấn văn bản")
        if kg_queries:
            parts.append(f"{len(kg_queries)} truy vấn đồ thị")
        steps.append({"title": "Truy xuất ngữ cảnh", "summary": "Đã chạy " + " và ".join(parts) + "."})
    if text_expanded or kg_expanded:
        steps.append({
            "title": "Mở rộng truy vấn",
            "summary": f"Sinh thêm {len(text_expanded) + len(kg_expanded)} truy vấn để kiểm tra bằng chứng.",
            "details": [*text_expanded, *kg_expanded][:8],
        })
    for key, title in (
        ("text_final_reasoning", "Suy luận từ văn bản"),
        ("kg_final_reasoning", "Suy luận từ đồ thị"),
        ("final_reasoning", "Suy luận cuối"),
    ):
        if reasoning.get(key):
            steps.append({"title": title, "summary": reasoning[key]})
    return steps


def openai_completion_response(req: OpenAIChatCompletionRequest, chat: ChatQueryResponse) -> dict[str, Any]:
    created = int(time.time())
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": created,
        "model": chat.mode or req.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": chat.answer},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "kgsauto": {
            "mode": chat.mode,
            "conversation_id": chat.conversation_id,
            "citations": chat.citations,
            "evidence": chat.evidence,
            "metadata": chat.metadata,
            "error": chat.error.model_dump() if chat.error else None,
        },
    }


async def openai_stream_events(req: OpenAIChatCompletionRequest):
    """Yield SSE events while the blocking RAG query runs, then stream the final answer."""

    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())
    model = req.mode or req.model

    def event(payload: dict[str, Any]) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def chunk(payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            **payload,
        }

    yield event(chunk({"choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]}))
    yield event(chunk({"choices": [{"index": 0, "delta": {}, "finish_reason": None}], "kgsauto": {"status": {"phase": "received", "message": "Đã nhận câu hỏi."}}}))
    yield event(chunk({"choices": [{"index": 0, "delta": {}, "finish_reason": None}], "kgsauto": {"status": {"phase": "retrieving", "message": "Đang truy xuất tài liệu và đồ thị tri thức..."}}}))

    chat = await query_openai_compatible(req)
    model = chat.mode or model

    yield event(chunk({"model": model, "choices": [{"index": 0, "delta": {}, "finish_reason": None}], "kgsauto": {"status": {"phase": "reasoning", "message": "Đang chuẩn hóa các bước reasoning..."}}}))
    reasoning_steps = _compact_reasoning_steps(chat.metadata.get("reasoning_steps") if chat.metadata else None)
    for index, step in enumerate(reasoning_steps):
        yield event(chunk({"model": model, "choices": [{"index": 0, "delta": {}, "finish_reason": None}], "kgsauto": {"reasoning_step": step, "reasoning_index": index}}))

    yield event(chunk({"model": model, "choices": [{"index": 0, "delta": {}, "finish_reason": None}], "kgsauto": {"status": {"phase": "answering", "message": "Đang stream câu trả lời..."}}}))
    for token in chat.answer.split(" "):
        if not token:
            continue
        yield event(chunk({"model": model, "choices": [{"index": 0, "delta": {"content": token + " "}, "finish_reason": None}]}))

    yield event(chunk({
        "model": model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        "kgsauto": {
            "mode": chat.mode,
            "conversation_id": chat.conversation_id,
            "citations": chat.citations,
            "evidence": chat.evidence,
            "metadata": {**chat.metadata, "reasoning_steps": reasoning_steps},
            "status": {"phase": "done", "message": "Hoàn tất."},
        },
    }))
    yield "data: [DONE]\n\n"


def error_response(error_type: str, message: str, req: ChatQueryRequest | None = None) -> ChatQueryResponse:
    return ChatQueryResponse(
        answer="",
        mode=req.mode if req else DEFAULT_MODE,
        conversation_id=req.conversation_id if req else None,
        citations=[],
        evidence=None,
        metadata={},
        error=ChatError(type=error_type, message=message),
    )
