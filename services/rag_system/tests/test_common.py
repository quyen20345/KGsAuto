"""Tests for common response/evidence helpers."""

import pytest
from services.rag_system.modes.common import (
    markdown_evidence,
    graph_evidence,
    empty_evidence,
    base_response,
)


class TestMarkdownEvidence:
    def test_converts_chunks_to_evidence(self):
        chunks = [
            {
                "chunk_id": "c1",
                "doc_id": "d1",
                "text": "content",
                "score": 0.9,
                "source_path": "/a.md",
                "title": "T",
                "section": "S",
                "metadata": {"k": "v"},
            }
        ]
        result = markdown_evidence(chunks)
        assert len(result) == 1
        assert result[0]["chunk_id"] == "c1"
        assert result[0]["score"] == 0.9

    def test_handles_none_values(self):
        chunks = [
            {
                "chunk_id": "c1",
                "doc_id": "d1",
                "text": "content",
                "score": None,
            }
        ]
        result = markdown_evidence(chunks)
        assert result[0]["score"] == 0.0


class TestGraphEvidence:
    def test_converts_facts_to_evidence(self):
        facts = [
            {
                "entity_id": "e1",
                "entity_name": "Entity",
                "fact_type": "property",
                "fact_text": "Some fact",
                "score": 0.85,
                "cypher_query": "MATCH...",
                "metadata": {"key": "val"},
            }
        ]
        result = graph_evidence(facts)
        assert len(result) == 1
        assert result[0]["entity_id"] == "e1"
        assert result[0]["score"] == 0.85

    def test_default_fact_type(self):
        facts = [{"entity_id": "e1", "entity_name": "Entity", "fact_text": "Fact", "score": 0.5}]
        result = graph_evidence(facts)
        assert result[0]["fact_type"] == "property"


class TestEmptyEvidence:
    def test_returns_empty_structure(self):
        result = empty_evidence()
        assert result["markdown_chunks"] == []
        assert result["graph_facts"] == []
        assert result["graph_context"] is None


class TestBaseResponse:
    def test_full_response(self):
        result = base_response(
            question="Q?",
            mode="semantic_search",
            answer_text="A",
            citations=["c1"],
            retrieval_time_ms=100.0,
            synthesis_time_ms=50.0,
            metadata={"m": "v"},
            evidence={"chunks": []},
            reasoning_steps=None,
        )
        assert result["question"] == "Q?"
        assert result["mode"] == "semantic_search"
        assert result["answer"] == "A"
        assert result["retrieval_time_ms"] == 100.0
        assert result["synthesis_time_ms"] == 50.0
