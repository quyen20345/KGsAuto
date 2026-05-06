"""Tests for GraphSearch keyword extraction failure behavior."""

import asyncio

import pytest

from services.rag_system.graph.graph_search import components
from services.rag_system.graph.neo4j_context_adapter import Neo4jAdapter


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
