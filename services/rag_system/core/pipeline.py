"""Compatibility wrapper for the unified retrieval pipeline."""

from services.rag_system.core.unified_pipeline import UnifiedRetrievalPipeline

RAGPipeline = UnifiedRetrievalPipeline

__all__ = ["RAGPipeline"]
