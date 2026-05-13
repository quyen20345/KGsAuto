"""Tests for RAG system schemas."""

import pytest
from services.rag_system.schemas import Chunk, MarkdownEvidence, GraphEvidence, Answer, RAGResponse


class TestChunk:
    def test_chunk_creation(self):
        chunk = Chunk(
            chunk_id="doc_0",
            doc_id="doc",
            source_path="/path/to/doc.md",
            title="Title",
            section="Section",
            text="Some content",
            metadata={"key": "value"},
            char_start=0,
            char_end=12,
            chunk_index=0,
        )
        assert chunk.chunk_id == "doc_0"
        assert chunk.doc_id == "doc"
        assert chunk.text == "Some content"


class TestMarkdownEvidence:
    def test_markdown_evidence_model_dump(self):
        evidence = MarkdownEvidence(
            chunk_id="chunk_1",
            text="Evidence text",
            score=0.95,
            section="Introduction",
            metadata={"author": "test"},
        )
        dumped = evidence.model_dump()
        assert dumped["chunk_id"] == "chunk_1"
        assert dumped["score"] == 0.95
        assert dumped["metadata"]["author"] == "test"


class TestGraphEvidence:
    def test_graph_evidence_model_dump(self):
        evidence = GraphEvidence(
            entity_id="entity_1",
            entity_name="Test Entity",
            fact_type="property",
            fact_text="Some fact",
            score=0.88,
            cypher_query="MATCH (n) RETURN n",
            metadata={"source": "test"},
        )
        dumped = evidence.model_dump()
        assert dumped["entity_id"] == "entity_1"
        assert dumped["fact_type"] == "property"
        assert dumped["score"] == 0.88


class TestAnswer:
    def test_answer_with_citations(self):
        answer = Answer(
            text="Answer with [citation1] and [citation2].",
            citations=["citation1", "citation2"],
            confidence=0.92,
            metadata={"model": "test-model"},
        )
        assert answer.text == "Answer with [citation1] and [citation2]."
        assert len(answer.citations) == 2

    def test_answer_default_values(self):
        answer = Answer(text="Simple answer")
        assert answer.citations == []
        assert answer.confidence is None
        assert answer.metadata == {}


class TestRAGResponse:
    def test_rag_response_structure(self):
        response = RAGResponse(
            question="What is the answer?",
            answer="The answer is 42.",
            mode="semantic_search",
            citations=["source1"],
            confidence=0.95,
            synthesis_time_ms=150.0,
            total_time_ms=250.0,
            token_usage=100,
            metadata={"test": True},
        )
        assert response.question == "What is the answer?"
        assert response.mode == "semantic_search"
        assert response.total_time_ms == 250.0
