import asyncio

import pytest

from services.rag_system.graph.neo4j_context_adapter import (
    Neo4jAdapter,
    deterministic_query_terms,
    normalize_vietnamese_text,
    split_identifier_variants,
)


def test_normalize_vietnamese_text_strips_diacritics_and_punctuation():
    assert normalize_vietnamese_text("Đại học Công nghệ") == "dai hoc cong nghe"
    assert normalize_vietnamese_text("  Trường--ĐH_Công.Nghệ  ") == "truong dh cong nghe"


def test_split_identifier_variants_handles_punctuation():
    assert split_identifier_variants("abc_uet_xyz") == ["abc_uet_xyz", "abc uet xyz", "abc", "uet", "xyz"]
    assert split_identifier_variants("uet-123") == ["uet-123", "uet 123", "uet", "123"]


def test_deterministic_query_terms_keeps_acronyms_and_normalized_variants():
    terms = deterministic_query_terms("UET co chuong trinh dao tao nao?", max_terms=20)

    assert "UET" in terms
    assert any(normalize_vietnamese_text(term) == "uet" for term in terms)
    assert "chuong trinh dao tao" in terms


def test_extract_keywords_uses_deterministic_fallback_when_llm_fails(monkeypatch):
    adapter = object.__new__(Neo4jAdapter)
    adapter.keyword_max_terms = 12

    async def failing_llm_keywords(query):
        raise RuntimeError("llm unavailable")

    monkeypatch.setattr(adapter, "_extract_llm_keywords", failing_llm_keywords)

    terms = asyncio.run(adapter._extract_keywords_async("UET co hoc bong nao?"))

    assert "UET" in terms
    assert any(normalize_vietnamese_text(term) == "uet" for term in terms)


def test_score_entity_prioritizes_exact_alias_over_description():
    adapter = object.__new__(Neo4jAdapter)
    adapter.description_fallback_min_term_length = 5
    alias_hit = {
        "id": "a",
        "name": "Trường Đại học Công nghệ",
        "properties": {"aliases": ["UET"], "description": ["Một trường thành viên"]},
    }
    description_hit = {
        "id": "b",
        "name": "Tin tuyển sinh",
        "properties": {"aliases": [], "description": ["Thông tin liên quan tới UET"]},
    }

    assert adapter._score_entity(alias_hit, ["UET"]) > adapter._score_entity(description_hit, ["UET"])


def test_search_entities_batch_calls_substring_fallback_when_fulltext_is_sparse(monkeypatch):
    adapter = object.__new__(Neo4jAdapter)
    adapter.fulltext_entity_index = "kg_entity_search"
    adapter.fulltext_candidate_limit = 50
    adapter.enable_substring_fallback = True
    adapter.substring_fallback_limit = 20
    adapter.top_k = 5
    adapter.description_fallback_min_term_length = 5
    adapter.allow_legacy_scan_fallback = True

    monkeypatch.setattr(adapter, "_has_index", lambda index_name: False)
    calls = []

    def fake_fallback(terms, exclude_ids, limit):
        calls.append((terms, exclude_ids, limit))
        return [
            {
                "id": "node_a",
                "name": "Trường Đại học Công nghệ",
                "labels": ["KGEntity"],
                "properties": {"aliases": ["UET"]},
                "fulltext_score": 0.0,
            }
        ]

    monkeypatch.setattr(adapter, "_search_entities_substring_fallback", fake_fallback)

    results = adapter._search_entities_batch(["UET"], limit=10)

    assert len(calls) == 1
    assert results[0]["id"] == "node_a"
    assert results[0]["score"] == 95.0


def test_aquery_context_uses_batched_graph_methods(monkeypatch):
    adapter = object.__new__(Neo4jAdapter)
    adapter.top_k = 2
    adapter.neighbor_limit_per_entity = 3
    adapter.enable_relationship_fulltext = True
    adapter._store = None

    async def fake_keywords(question):
        return ["UET"]

    def fake_entities_batch(keywords, limit):
        return [
            {
                "id": "node_a",
                "name": "Trường Đại học Công nghệ",
                "labels": ["KGEntity"],
                "properties": {"aliases": ["UET"], "description": ["Graph description"]},
                "score": 95,
            }
        ]

    def fake_relationships_batch(entity_ids, limit_per_entity):
        assert entity_ids == ["node_a"]
        assert limit_per_entity == 3
        return []

    def fake_relationships_search(keywords, limit):
        return []

    def fake_chunks(question):
        return []

    monkeypatch.setattr(adapter, "_extract_keywords_async", fake_keywords)
    monkeypatch.setattr(adapter, "_search_entities_batch", fake_entities_batch)
    monkeypatch.setattr(adapter, "_get_relationships_batch", fake_relationships_batch)
    monkeypatch.setattr(adapter, "_search_relationships_batch", fake_relationships_search)
    monkeypatch.setattr(adapter, "_search_chunks", fake_chunks)

    context = asyncio.run(adapter.aquery_context("UET"))

    assert "Trường Đại học Công nghệ" in context
    assert "UET" in context
