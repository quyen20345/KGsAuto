"""RAG System - Retrieval-Augmented Generation for UET Knowledge Base."""

from __future__ import annotations

from importlib import import_module

from services.rag_system.config import RAGConfig
from services.rag_system.schemas import (
    Answer,
    Chunk,
    GraphEvidence,
    MarkdownEvidence,
    RAGResponse,
    RetrievalResult,
)

_LAZY_EXPORTS = {
    "RAGPipeline": ("services.rag_system.core.pipeline", "RAGPipeline"),
    "UnifiedRetrievalPipeline": ("services.rag_system.core.unified_pipeline", "UnifiedRetrievalPipeline"),
    "DocumentStore": ("services.rag_system.storage.document", "DocumentStore"),
    "GraphStore": ("services.rag_system.storage.graph", "GraphStore"),
    "MarkdownChunker": ("services.rag_system.retrieval.chunking", "MarkdownChunker"),
    "MarkdownIndexer": ("services.rag_system.retrieval.indexing", "MarkdownIndexer"),
    "MarkdownRetriever": ("services.rag_system.retrieval.markdown", "MarkdownRetriever"),
    "GraphRetriever": ("services.rag_system.retrieval.graph", "GraphRetriever"),
    "HybridRetriever": ("services.rag_system.retrieval.hybrid", "HybridRetriever"),
    "AnswerSynthesizer": ("services.rag_system.components.synthesis", "AnswerSynthesizer"),
    "EvaluationMetrics": ("services.rag_system.evaluation.metrics", "EvaluationMetrics"),
    "BenchmarkResults": ("services.rag_system.evaluation.metrics", "BenchmarkResults"),
    "RAGEvaluator": ("services.rag_system.evaluation.metrics", "RAGEvaluator"),
}

__all__ = [
    "RAGConfig",
    "RAGPipeline",
    "UnifiedRetrievalPipeline",
    "Chunk",
    "MarkdownEvidence",
    "GraphEvidence",
    "RetrievalResult",
    "Answer",
    "RAGResponse",
    "DocumentStore",
    "GraphStore",
    "MarkdownChunker",
    "MarkdownIndexer",
    "MarkdownRetriever",
    "GraphRetriever",
    "HybridRetriever",
    "AnswerSynthesizer",
    "EvaluationMetrics",
    "BenchmarkResults",
    "RAGEvaluator",
]


def __getattr__(name: str):
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = _LAZY_EXPORTS[name]
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value
