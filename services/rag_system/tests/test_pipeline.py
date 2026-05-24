"""Tests for UnifiedRetrievalPipeline."""

# pyrefly: ignore [missing-import]
import pytest
from unittest.mock import MagicMock, patch
from services.rag_system.pipeline import UnifiedRetrievalPipeline, canonical_unified_mode
from services.rag_system.config import RAGConfig


class TestCanonicalUnifiedMode:
    def test_valid_modes(self):
        assert canonical_unified_mode("semantic_search") == "semantic_search"
        assert canonical_unified_mode("graph_search") == "graph_search"
        assert canonical_unified_mode("naive_grag") == "naive_grag"
        assert canonical_unified_mode("hybrid") == "hybrid"
        assert canonical_unified_mode("direct") == "direct"
        
    def test_whitespace_handling(self):
        assert canonical_unified_mode("  semantic_search  ") == "semantic_search"
        
    def test_case_handling(self):
        # Default behavior is case-sensitive for valid modes
        assert canonical_unified_mode("SEMANTIC_SEARCH") == "semantic_search"
        
    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError, match="Unsupported unified retrieval mode"):
            canonical_unified_mode("invalid_mode")


class TestUnifiedRetrievalPipeline:
    @pytest.fixture
    def pipeline(self):
        config = RAGConfig()
        return UnifiedRetrievalPipeline(config)
    
    @pytest.fixture
    def mock_markdown_retriever(self):
        mock = MagicMock()
        mock.retrieve.return_value = [
            {"chunk_id": "c1", "text": "Test content", "score": 0.9}
        ]
        return mock
    
    @pytest.fixture
    def mock_synthesizer(self):
        from services.rag_system.schemas import Answer
        mock = MagicMock()
        mock.synthesize_markdown_only.return_value = Answer(
            text="Test answer",
            citations=["c1"],
            metadata={"model": "test"}
        )
        return mock
    
    def test_semantic_search_mode(self, pipeline, mock_markdown_retriever, mock_synthesizer):
        pipeline.markdown_retriever = mock_markdown_retriever
        pipeline.synthesizer = mock_synthesizer
        
        result = pipeline.query("Test question?", mode="semantic_search", top_k=3)
        
        assert result["question"] == "Test question?"
        assert result["mode"] == "semantic_search"
        assert result["answer"] == "Test answer"
        assert "c1" in result["citations"]
        assert "total_time_ms" in result
        assert "retrieval_time_ms" in result
        assert "synthesis_time_ms" in result
        
        mock_markdown_retriever.retrieve.assert_called_once_with("Test question?", top_k=3)

    def test_response_includes_evidence_when_requested(self, pipeline, mock_markdown_retriever, mock_synthesizer):
        pipeline.markdown_retriever = mock_markdown_retriever
        pipeline.synthesizer = mock_synthesizer
        
        result = pipeline.query("Test?", mode="semantic_search", include_evidence=True)
        
        assert result["evidence"] is not None
        assert "markdown_chunks" in result["evidence"]
        
    def test_response_excludes_evidence_when_not_requested(self, pipeline, mock_markdown_retriever, mock_synthesizer):
        pipeline.markdown_retriever = mock_markdown_retriever
        pipeline.synthesizer = mock_synthesizer
        
        result = pipeline.query("Test?", mode="semantic_search", include_evidence=False)
        
        assert result["evidence"] is None

    def test_default_top_k_from_config(self, pipeline, mock_markdown_retriever, mock_synthesizer):
        pipeline.markdown_retriever = mock_markdown_retriever
        pipeline.synthesizer = mock_synthesizer
        
        pipeline.query("Test?", mode="semantic_search", top_k=None)
        
        # Should use config default (5)
        mock_markdown_retriever.retrieve.assert_called_once_with("Test?", top_k=5)


class TestPipelineModes:
    """Test that all modes dispatch correctly."""
    
    def test_mode_dispatch_semantic(self):
        with patch("services.rag_system.pipeline.run_semantic_search") as mock:
            mock.return_value = {"answer": "test", "mode": "semantic_search"}
            pipeline = UnifiedRetrievalPipeline()
            result = pipeline.query("Q?", mode="semantic_search")
            mock.assert_called_once()
            
    def test_mode_dispatch_graph_search(self):
        with patch("services.rag_system.pipeline.run_graph_search") as mock:
            mock.return_value = {"answer": "test", "mode": "graph_search"}
            pipeline = UnifiedRetrievalPipeline()
            result = pipeline.query("Q?", mode="graph_search")
            mock.assert_called_once()
            
    def test_mode_dispatch_naive_grag(self):
        with patch("services.rag_system.pipeline.run_naive_grag") as mock:
            mock.return_value = {"answer": "test", "mode": "naive_grag"}
            pipeline = UnifiedRetrievalPipeline()
            result = pipeline.query("Q?", mode="naive_grag")
            mock.assert_called_once()
            
    def test_mode_dispatch_hybrid(self):
        with patch("services.rag_system.pipeline.run_hybrid") as mock:
            mock.return_value = {"answer": "test", "mode": "hybrid"}
            pipeline = UnifiedRetrievalPipeline()
            result = pipeline.query("Q?", mode="hybrid")
            mock.assert_called_once()

    def test_mode_dispatch_direct(self):
        with patch("services.rag_system.pipeline.run_direct") as mock:
            mock.return_value = {"answer": "test", "mode": "direct"}
            pipeline = UnifiedRetrievalPipeline()
            result = pipeline.query("Q?", mode="direct")
            mock.assert_called_once()
