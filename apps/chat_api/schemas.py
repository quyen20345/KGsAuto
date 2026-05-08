from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatError(BaseModel):
    type: str
    message: str


class ChatQueryRequest(BaseModel):
    message: str = Field(..., min_length=1)
    mode: str = "semantic_search"
    top_k: int = Field(default=5, ge=1, le=20)
    include_evidence: bool = False
    conversation_id: str | None = None


class ChatQueryResponse(BaseModel):
    answer: str
    mode: str
    conversation_id: str | None = None
    citations: list[str] = []
    evidence: dict[str, Any] | None = None
    metadata: dict[str, Any] = {}
    error: ChatError | None = None


class ChatModesResponse(BaseModel):
    modes: list[str]
    default_mode: str


class ChatHealthResponse(BaseModel):
    status: str
    service: str
    modes: list[str]
