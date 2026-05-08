from __future__ import annotations

from typing import Any

from services.rag_system import RAGConfig, UnifiedRetrievalPipeline
from services.rag_system.pipeline import UNIFIED_MODES, canonical_unified_mode

from apps.chat_api.schemas import ChatError, ChatQueryRequest, ChatQueryResponse


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
