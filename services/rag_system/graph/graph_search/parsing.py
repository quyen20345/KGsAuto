"""Parsing helpers for GraphSearch LLM module outputs."""

from __future__ import annotations

import ast
import json
import re
from typing import Any


SUB_QUERY_RE = re.compile(r'"?Sub-query\s+\d+"?\s*:\s*"([^"]+)"', re.IGNORECASE)
PLACEHOLDER_RE = re.compile(r"\bEntity#\d+\b|#\d+")
KEYWORD_FIELDS = (
    "high_level_keywords",
    "low_level_keywords",
    "expanded_keywords",
    "must_keep_phrases",
)


def _without_code_fence(text: str) -> str:
    stripped = text.strip()
    fence = re.match(r"^```(?:json|python)?\s*(.*?)\s*```$", stripped, re.DOTALL | re.IGNORECASE)
    return fence.group(1).strip() if fence else stripped


def _extract_balanced(text: str, opener: str, closer: str) -> str | None:
    start = text.find(opener)
    if start < 0:
        return None

    depth = 0
    in_string = False
    quote = ""
    escaped = False
    for index, char in enumerate(text[start:], start=start):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                in_string = False
            continue
        if char in {"'", '"'}:
            in_string = True
            quote = char
        elif char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    return None


def _loads_structured(text: str) -> Any:
    cleaned = _without_code_fence(text)
    candidates = [
        cleaned,
        _extract_balanced(cleaned, "{", "}"),
        _extract_balanced(cleaned, "[", "]"),
    ]

    for candidate in candidates:
        if not candidate:
            continue
        for loader in (json.loads, ast.literal_eval):
            try:
                return loader(candidate)
            except Exception:
                continue
    return None


def _ordered_values(parsed: Any) -> list[Any]:
    if isinstance(parsed, dict):
        return list(parsed.values())
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, str):
        return [parsed]
    return []


def parse_semantic_sub_queries(text: str, max_items: int = 5) -> list[str]:
    """Parse QD output into standalone semantic sub-queries."""
    parsed = _loads_structured(text)
    values = _ordered_values(parsed)
    queries = [str(value).strip() for value in values if str(value).strip()]

    if not queries:
        queries = [match.strip() for match in SUB_QUERY_RE.findall(text) if match.strip()]

    return queries[:max_items]


def _format_triple(item: Any) -> str:
    if isinstance(item, (list, tuple)):
        parts = [str(part).strip() for part in item if str(part).strip()]
        return " ".join(parts)
    if isinstance(item, dict):
        parts = [str(value).strip() for value in item.values() if str(value).strip()]
        return " ".join(parts)
    return str(item).strip()


def format_relational_query(value: Any) -> str:
    """Convert triple-like output into a retrieval query string."""
    if isinstance(value, (list, tuple)):
        if len(value) >= 3 and all(not isinstance(item, (list, tuple, dict)) for item in value[:3]):
            return _format_triple(value)
        parts = [_format_triple(item) for item in value]
        return "; ".join(part for part in parts if part)
    return _format_triple(value)


def parse_relational_sub_queries(text: str, max_items: int = 5) -> list[str]:
    """Parse KG QD output while accepting JSON arrays or Python tuple syntax."""
    parsed = _loads_structured(text)
    queries = [format_relational_query(value) for value in _ordered_values(parsed)]
    queries = [query for query in queries if query]

    if not queries:
        array_matches = re.findall(
            r'"?Sub-query\s+\d+"?\s*:\s*(\[[\s\S]*?\])(?=,?\s*"?Sub-query|\s*\})',
            text,
            flags=re.IGNORECASE,
        )
        for match in array_matches:
            parsed_match = _loads_structured(match)
            query = format_relational_query(parsed_match if parsed_match is not None else match)
            if query:
                queries.append(query)

    return queries[:max_items]


def parse_expanded_queries(text: str, max_items: int = 3) -> list[str]:
    """Parse QE output into a bounded list of expansion queries."""
    parsed = _loads_structured(text)
    values = _ordered_values(parsed)
    queries = [str(value).strip() for value in values if str(value).strip()]
    if not queries and text.strip():
        queries = [text.strip()]
    return queries[:max_items]


def _keyword_values(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, dict):
        return list(value.values())
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _clean_keyword_list(value: Any, max_items: int) -> list[str]:
    seen: set[str] = set()
    keywords: list[str] = []
    for item in _keyword_values(value):
        text = " ".join(str(item).split())
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        keywords.append(text)
        if len(keywords) >= max_items:
            break
    return keywords


def parse_keyword_extraction(
    text: str,
    max_high_level: int = 6,
    max_low_level: int = 10,
    max_expanded: int = 10,
    max_phrases: int = 8,
) -> dict[str, list[str]]:
    """Parse keyword extraction output into bounded structured keyword groups."""
    empty = {field: [] for field in KEYWORD_FIELDS}
    parsed = _loads_structured(text)
    if not isinstance(parsed, dict):
        return empty

    limits = {
        "high_level_keywords": max_high_level,
        "low_level_keywords": max_low_level,
        "expanded_keywords": max_expanded,
        "must_keep_phrases": max_phrases,
    }
    return {
        field: _clean_keyword_list(parsed.get(field), limits[field])
        for field in KEYWORD_FIELDS
    }


def relational_query_to_retrieval_text(query: str) -> str:
    """Remove unresolved placeholders but preserve Vietnamese/entity text."""
    cleaned = PLACEHOLDER_RE.sub(" ", query)
    return " ".join(cleaned.replace(";", " ").split())
