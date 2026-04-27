"""Small utilities shared by the Neo4j GraphSearch runtime."""

from __future__ import annotations

import os
import re
import string
from typing import Any

from dotenv import load_dotenv

load_dotenv()

LLM_BASE_URL = os.getenv("ROUTER9_BASE_URL", "http://192.168.190.8:8000/v1/")
LLM_API_KEY = os.getenv("ROUTER9_API_KEY", "NONE")
MODEL_NAME = os.getenv("ROUTER9_MODEL", "Qwen2.5-32B-Instruct")


async def openai_complete(
    prompt: str,
    model: str | None = None,
    system_prompt: str | None = None,
    history_messages: list[dict[str, str]] | None = None,
    temperature: float = 0.0,
    **kwargs: Any,
) -> str:
    """Call the configured OpenAI-compatible chat endpoint."""
    from openai import AsyncOpenAI

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.extend(history_messages or [])
    messages.append({"role": "user", "content": prompt})

    async with AsyncOpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL) as client:
        response = await client.chat.completions.create(
            model=model or MODEL_NAME,
            messages=messages,
            temperature=temperature,
            **kwargs,
        )
    return response.choices[0].message.content or ""


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
