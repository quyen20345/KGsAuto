"""Tests for GraphSearch keyword extraction failure behavior."""

import asyncio

import pytest

from services.rag_system.graph.graph_search import components
from services.rag_system.graph.neo4j_context_adapter import Neo4jAdapter


class FakeStore:
    def __init__(self):
        self.query = None
        self.top_k = None

    def collection_exists(self):
        return True

    def search(self, query, top_k=5):
        self.query = query
        self.top_k = top_k
        return [
            {
                "chunk_id": "doc_a_0",
                "doc_id": "doc_a",
                "source_path": "/docs/doc_a.md",
                "title": "Doc A",
                "section": "Intro",
                "text": "Qdrant chunk content",
                "score": 0.91,
            }
        ]


def test_keywords_extraction_rejects_empty_keyword_response(monkeypatch):
    async def fake_complete(prompt, **kwargs):
        return '{"must_keep_phrases": [], "low_level_keywords": [], "expanded_keywords": [], "high_level_keywords": []}'

    monkeypatch.setattr(components, "openai_complete", fake_complete)

    with pytest.raises(components.GraphKeywordExtractionError, match="no parseable keywords"):
        asyncio.run(components.keywords_extraction("Open Workshop Ericsson Vietnam"))


def test_adapter_keyword_extraction_times_out(monkeypatch):
    adapter = object.__new__(Neo4jAdapter)
    adapter.keyword_timeout_seconds = 0.01

    async def slow_keywords_extraction(query):
        await asyncio.sleep(1)
        return {
            "must_keep_phrases": ["Ericsson Vietnam"],
            "low_level_keywords": [],
            "expanded_keywords": [],
            "high_level_keywords": [],
        }

    monkeypatch.setattr(components, "keywords_extraction", slow_keywords_extraction)

    with pytest.raises(RuntimeError, match="timed out"):
        asyncio.run(adapter._extract_llm_keywords("Ericsson Vietnam được chứng nhận năm nào?"))


def test_adapter_rejects_empty_keywords(monkeypatch):
    adapter = object.__new__(Neo4jAdapter)
    adapter.keyword_max_terms = 12

    async def empty_llm_keywords(query):
        return {
            "must_keep_phrases": [],
            "low_level_keywords": [],
            "expanded_keywords": [],
            "high_level_keywords": [],
        }

    monkeypatch.setattr(adapter, "_extract_llm_keywords", empty_llm_keywords)

    with pytest.raises(RuntimeError, match="returned no keywords"):
        asyncio.run(adapter._extract_keywords_async("Open Workshop Ericsson Vietnam"))


def test_adapter_loads_document_chunks_from_qdrant(monkeypatch):
    adapter = object.__new__(Neo4jAdapter)
    adapter.top_k = 2
    adapter._store = FakeStore()

    async def fake_keywords(question):
        return ["keyword"]

    async def fake_entities(keyword, limit):
        return [{"id": "node_a"}]

    async def fake_entity_details(entity_id):
        return {
            "id": entity_id,
            "name": "Node A",
            "labels": ["ENTITY"],
            "properties": {"description": ["Graph description"], "chunk_id": ["legacy_doc_id"]},
            "score": 100,
        }

    async def fake_relationships(entity_id, limit):
        return []

    async def fake_search_relationships(keyword, limit):
        return []

    monkeypatch.setattr(adapter, "_extract_keywords_async", fake_keywords)
    monkeypatch.setattr(adapter, "_asearch_entities", fake_entities)
    monkeypatch.setattr(adapter, "_aget_entity_details", fake_entity_details)
    monkeypatch.setattr(adapter, "_aget_relationships", fake_relationships)
    monkeypatch.setattr(adapter, "_asearch_relationships", fake_search_relationships)

    context = asyncio.run(adapter.aquery_context("original question"))

    assert not hasattr(adapter, "_load_markdown_chunk")
    assert adapter._store.query == "original question"
    assert adapter._store.top_k == 2
    assert "Qdrant chunk content" in context
    assert "doc_a_0" in context
    assert "legacy_doc_id" in context
