"""Supported user-facing RAG modes."""

from __future__ import annotations


UNIFIED_MODES = {"semantic_search", "graph_search", "naive_grag", "hybrid"}
MODE_ALIASES: dict[str, str] = {}


def canonical_unified_mode(mode: str) -> str:
    """Normalize and validate a user-facing retrieval mode name."""

    canonical = MODE_ALIASES.get(mode.strip().lower(), mode.strip().lower())
    if canonical not in UNIFIED_MODES:
        supported = ", ".join(sorted(UNIFIED_MODES))
        raise ValueError(f"Unsupported unified retrieval mode: {mode}. Supported modes: {supported}")
    return canonical


__all__ = ["MODE_ALIASES", "UNIFIED_MODES", "canonical_unified_mode"]
