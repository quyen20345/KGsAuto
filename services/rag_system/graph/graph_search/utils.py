"""Small utilities shared by the Neo4j GraphSearch runtime."""

from __future__ import annotations

import re
import string
from typing import Any

from services.llms import get_llm


def _get_llm_client(model_name: str | None = None, temperature: float | None = None):
    """Get the unified LLM client from RAG config / env defaults."""
    from services.rag_system.config import RAGConfig

    config = RAGConfig()
    return get_llm(
        config.llm_provider,
        model_name=model_name or config.llm_model,
        temperature=config.llm_temperature if temperature is None else temperature,
    )


async def openai_complete(
    prompt: str,
    model: str | None = None,
    system_prompt: str | None = None,
    history_messages: list[dict[str, str]] | None = None,
    temperature: float = 0.0,
    **kwargs: Any,
) -> str:
    """Call the configured LLM via the unified services.llms client."""
    # Build combined prompt if history messages are provided
    effective_prompt = prompt
    if history_messages:
        parts = []
        for msg in history_messages:
            role = msg.get("role", "user")
            parts.append(f"[{role}]: {msg.get('content', '')}")
        parts.append(f"[user]: {prompt}")
        effective_prompt = "\n".join(parts)

    llm = _get_llm_client(model, temperature=temperature)
    response = await llm.agenerate(
        prompt=effective_prompt,
        system_prompt=system_prompt,
        temperature=temperature,
    )
    return response.content or ""


def format_history_context(history: list[tuple[str, str, str]]) -> str:
    parts = []
    for index, (question, context_summary, answer) in enumerate(history, start=1):
        parts.append(
            f"Sub-query {index}: {question}\n"
            f"Retrieved context:\n{context_summary}\n"
            f"Sub-query answer: {answer}"
        )
    return "\n\n".join(parts).strip()


def normalize(text: str) -> list[str]:
    """Normalize text into lowercase punctuation-free tokens."""

    def remove_articles(value: str) -> str:
        return re.sub(r"\b(a|an|the)\b", " ", value)

    def remove_punctuation(value: str) -> str:
        exclude = set(string.punctuation)
        return "".join(char for char in value if char not in exclude)

    cleaned = remove_articles(remove_punctuation(text.lower()))
    return " ".join(cleaned.split()).split()
