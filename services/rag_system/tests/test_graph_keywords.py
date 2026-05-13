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
                "section": "Intro",
                "text": "Qdrant chunk content",
                "score": 0.91,
            }
        ]


def test_keywords_extraction_falls_back_when_repair_is_empty(monkeypatch):
    calls = []

    async def fake_complete(prompt, **kwargs):
        calls.append(prompt)
        return '{"must_keep_phrases": [], "low_level_keywords": [], "expanded_keywords": [], "high_level_keywords": []}'

    monkeypatch.setattr(components, "openai_complete", fake_complete)

    result = asyncio.run(components.keywords_extraction("Open Workshop Ericsson Vietnam"))

    assert len(calls) == 2
    assert result["must_keep_phrases"] == ["Open Workshop Ericsson Vietnam"]


def test_keywords_extraction_repairs_empty_keyword_response(monkeypatch):
    responses = iter(
        [
            "[]",
            '{"must_keep_phrases": ["Open Workshop"], "low_level_keywords": ["Ericsson Vietnam"], '
            '"expanded_keywords": [], "high_level_keywords": ["Internship 2022"]}',
        ]
    )
    prompts = []

    async def fake_complete(prompt, **kwargs):
        prompts.append(prompt)
        return next(responses)

    monkeypatch.setattr(components, "openai_complete", fake_complete)

    result = asyncio.run(components.keywords_extraction("Open Workshop Ericsson Vietnam"))

    assert result["must_keep_phrases"] == ["Open Workshop"]
    assert result["low_level_keywords"] == ["Ericsson Vietnam"]
    assert result["high_level_keywords"] == ["Internship 2022"]
    assert len(prompts) == 2
    assert "Invalid previous output" in prompts[1]


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


def test_adapter_uses_deterministic_terms_when_llm_returns_empty(monkeypatch):
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

    result = asyncio.run(adapter._extract_keywords_async("Open Workshop Ericsson Vietnam"))

    assert "Open Workshop Ericsson Vietnam" in result


def test_adapter_loads_document_chunks_from_qdrant(monkeypatch):
    adapter = object.__new__(Neo4jAdapter)
    adapter.top_k = 2
    adapter._store = FakeStore()

    adapter.neighbor_limit_per_entity = 4
    adapter.enable_relationship_fulltext = True

    async def fake_keywords(question):
        return ["keyword"]

    def fake_entities(keywords, limit):
        return [
            {
                "id": "node_a",
                "name": "Node A",
                "labels": ["ENTITY"],
                "properties": {"description": ["Graph description"], "chunk_id": ["legacy_doc_id"]},
                "score": 100,
            }
        ]

    def fake_relationships(entity_ids, limit_per_entity):
        return []

    def fake_search_relationships(keywords, limit):
        return []

    monkeypatch.setattr(adapter, "_extract_keywords_async", fake_keywords)
    monkeypatch.setattr(adapter, "_search_entities_batch", fake_entities)
    monkeypatch.setattr(adapter, "_get_relationships_batch", fake_relationships)
    monkeypatch.setattr(adapter, "_search_relationships_batch", fake_search_relationships)

    context = asyncio.run(adapter.aquery_context("original question"))

    assert not hasattr(adapter, "_load_markdown_chunk")
    assert adapter._store.query == "original question"
    assert adapter._store.top_k == 2
    assert "Qdrant chunk content" in context
    assert "doc_a_0" in context
    assert "legacy_doc_id" in context
