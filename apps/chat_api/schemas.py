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


class OpenAIChatMessage(BaseModel):
    role: str
    content: str | list[dict[str, Any]] | None = None


class OpenAIChatCompletionRequest(BaseModel):
    model: str = "semantic_search"
    messages: list[OpenAIChatMessage]
    stream: bool = False
    temperature: float | None = None
    max_tokens: int | None = None

    # KGsAuto-specific optional knobs. OpenAI-compatible clients will ignore
    # them, but custom UIs can pass them through the same endpoint.
    mode: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)
    include_evidence: bool = False
    conversation_id: str | None = None


class OpenAIModel(BaseModel):
    id: str
    object: str = "model"
    created: int = 0
    owned_by: str = "kgsauto"


class OpenAIModelsResponse(BaseModel):
    object: str = "list"
    data: list[OpenAIModel]


class AskRequest(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_id: str | None = None


class AskResponse(BaseModel):
    answer: str
    conversation_id: str | None = None
