"""RAG System - Retrieval-Augmented Generation for UET Knowledge Base."""

from __future__ import annotations

from importlib import import_module

from services.rag_system.config import RAGConfig

_LAZY_EXPORTS = {
    "UnifiedRetrievalPipeline": ("services.rag_system.pipeline", "UnifiedRetrievalPipeline"),
}

__all__ = [
    "RAGConfig",
    "UnifiedRetrievalPipeline",
]


def __getattr__(name: str):
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = _LAZY_EXPORTS[name]
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value
