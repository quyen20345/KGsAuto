from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from services.entity_resolution.preprocessing.normalize import normalize_text


@dataclass(frozen=True)
class _NameCandidate:
    text: str
    key: str
    tokens: set[str]
    frequency: int
    is_preferred: bool


def select_canonical_name(candidates: list[str], preferred_names: list[str] | None = None) -> str:
    valid_candidates = [normalize_text(candidate) for candidate in candidates]
    valid_candidates = [candidate for candidate in valid_candidates if candidate]
    if not valid_candidates:
        return ""

    preferred_keys = {
        _name_key(name)
        for name in (preferred_names or [])
        if normalize_text(name)
    }

    grouped = _group_candidates(valid_candidates, preferred_keys)
    if len(grouped) == 1:
        return grouped[0].text

    return max(
        grouped,
        key=lambda candidate: (
            _score_candidate(candidate, grouped),
            candidate.is_preferred,
            -abs(len(candidate.text) - 35),
            -len(candidate.text),
            _display_quality(candidate.text),
            candidate.text,
        ),
    ).text


def _group_candidates(candidates: list[str], preferred_keys: set[str]) -> list[_NameCandidate]:
    counts = Counter(_name_key(candidate) for candidate in candidates)
    display_by_key: dict[str, str] = {}

    for candidate in candidates:
        key = _name_key(candidate)
        current = display_by_key.get(key)
        if current is None or _display_quality(candidate) > _display_quality(current):
            display_by_key[key] = candidate

    return [
        _NameCandidate(
            text=display,
            key=key,
            tokens=_tokens(display),
            frequency=counts[key],
            is_preferred=key in preferred_keys,
        )
        for key, display in display_by_key.items()
    ]


def _score_candidate(candidate: _NameCandidate, all_candidates: list[_NameCandidate]) -> float:
    score = candidate.frequency * 2.0

    if candidate.is_preferred:
        score += 1.5

    score += _alias_fit_score(candidate, all_candidates)
    score -= _short_name_penalty(candidate)
    score -= _long_name_penalty(candidate)

    return score


def _alias_fit_score(candidate: _NameCandidate, all_candidates: list[_NameCandidate]) -> float:
    if not candidate.tokens:
        return 0.0

    score = 0.0
    for other in all_candidates:
        if other.key == candidate.key or not other.tokens:
            continue

        overlap = len(candidate.tokens & other.tokens)
        if overlap == len(candidate.tokens) and len(other.tokens) > len(candidate.tokens):
            score += 1.5
        elif overlap == len(other.tokens):
            score += 0.5
        elif overlap:
            score += overlap / max(len(other.tokens), 1) * 0.25

    return min(score, 3.0)


def _short_name_penalty(candidate: _NameCandidate) -> float:
    text = candidate.text.strip()
    token_count = len(candidate.tokens)

    if len(text) <= 3:
        return 4.0
    if token_count == 1 and text.isupper() and len(text) <= 6:
        return 3.0
    if token_count <= 2 and len(text) <= 8:
        return 1.5
    return 0.0


def _long_name_penalty(candidate: _NameCandidate) -> float:
    text = candidate.text.strip()
    token_count = len(candidate.tokens)
    punctuation_count = sum(text.count(mark) for mark in [",", ";", ":", "."])

    penalty = 0.0
    if len(text) > 90:
        penalty += 3.0
    elif len(text) > 65:
        penalty += 1.5

    if token_count > 12:
        penalty += 2.0
    elif token_count > 9:
        penalty += 1.0

    if punctuation_count >= 2:
        penalty += 1.0

    if re.search(r"\b(là|thuộc|được|refers|same|under|located|based)\b", text, re.IGNORECASE):
        penalty += 2.0

    return penalty


def _display_quality(text: str) -> tuple[int, int, int]:
    return (
        sum(1 for char in text if char.isupper()),
        sum(1 for char in text if char.isalpha()),
        -len(text),
    )


def _name_key(name: str) -> str:
    return normalize_text(name).casefold()


def _tokens(name: str) -> set[str]:
    return {token.casefold() for token in re.findall(r"\w+", normalize_text(name)) if len(token) > 1}
