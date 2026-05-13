"""Tests for graph search parsing utilities."""

import pytest
from services.rag_system.graph.graph_search.parsing import (
    parse_semantic_sub_queries,
    parse_relational_sub_queries,
    parse_expanded_queries,
    parse_keyword_extraction,
    format_relational_query,
    relational_query_to_retrieval_text,
)


class TestParseSemanticSubQueries:
    def test_parse_json_object(self):
        text = '{"Sub-query 1": "Who is the president?", "Sub-query 2": "When was he elected?"}'
        result = parse_semantic_sub_queries(text, max_items=5)
        assert len(result) == 2
        assert "Who is the president?" in result
        assert "When was he elected?" in result

    def test_parse_regex_fallback(self):
        text = 'Sub-query 1: "What is the capital?"\nSub-query 2: "How many people live there?"'
        result = parse_semantic_sub_queries(text, max_items=5)
        assert len(result) == 2
        assert "What is the capital?" in result

    def test_max_items_limit(self):
        text = '{"1": "a", "2": "b", "3": "c", "4": "d", "5": "e", "6": "f"}'
        result = parse_semantic_sub_queries(text, max_items=3)
        assert len(result) == 3


class TestParseRelationalSubQueries:
    def test_parse_triple_format(self):
        text = '{"Sub-query 1": [("Entity1", "relation", "Entity2")]}'
        result = parse_relational_sub_queries(text, max_items=5)
        assert len(result) >= 1
        assert "Entity1 relation Entity2" in result[0]

    def test_parse_array_format(self):
        text = '{"Sub-query 1": [["A", "connected_to", "B"]]}'
        result = parse_relational_sub_queries(text, max_items=5)
        assert len(result) >= 1


class TestParseExpandedQueries:
    def test_parse_simple_list(self):
        text = '["query 1", "query 2", "query 3"]'
        result = parse_expanded_queries(text, max_items=5)
        assert len(result) == 3

    def test_fallback_to_whole_text(self):
        text = "What is the meaning of life?"
        result = parse_expanded_queries(text, max_items=3)
        assert len(result) == 1
        assert result[0] == text

    def test_max_items_respected(self):
        text = '["q1", "q2", "q3", "q4", "q5"]'
        result = parse_expanded_queries(text, max_items=3)
        assert len(result) == 3


class TestParseKeywordExtraction:
    def test_full_keyword_extraction(self):
        text = '''{
            "high_level_keywords": ["education", "university"],
            "low_level_keywords": ["UET", "Hanoi"],
            "expanded_keywords": ["college", "school"],
            "must_keep_phrases": ["University of Engineering"]
        }'''
        result = parse_keyword_extraction(text)
        assert "high_level_keywords" in result
        assert "low_level_keywords" in result
        assert "UET" in result["low_level_keywords"]
        assert "University of Engineering" in result["must_keep_phrases"]

    def test_invalid_input_returns_empty(self):
        text = "not valid json"
        result = parse_keyword_extraction(text)
        assert result["high_level_keywords"] == []
        assert result["low_level_keywords"] == []

    def test_parse_fenced_keyword_list_as_low_level_keywords(self):
        text = '```json ["Open Workshop", "Ericsson Vietnam"] ```'
        result = parse_keyword_extraction(text)
        assert result["low_level_keywords"] == ["Open Workshop", "Ericsson Vietnam"]

    def test_parse_keyword_alias_keys(self):
        text = '''{
            "entities": ["Học bổng Đinh Thiện Lý"],
            "keywords": ["quản lý bởi"],
            "aliases": ["hoc bong Dinh Thien Ly"],
            "topics": ["học bổng"]
        }'''
        result = parse_keyword_extraction(text)
        assert result["must_keep_phrases"] == ["Học bổng Đinh Thiện Lý"]
        assert result["low_level_keywords"] == ["quản lý bởi"]
        assert result["expanded_keywords"] == ["hoc bong Dinh Thien Ly"]
        assert result["high_level_keywords"] == ["học bổng"]


class TestFormatRelationalQuery:
    def test_format_triple(self):
        result = format_relational_query(["A", "relates_to", "B"])
        assert "A" in result
        assert "B" in result

    def test_format_nested_list(self):
        result = format_relational_query([["A", "to", "B"], ["C", "to", "D"]])
        assert "A" in result or "C" in result

    def test_format_simple_string(self):
        result = format_relational_query("simple query")
        assert result == "simple query"


class TestRelationalQueryToRetrievalText:
    def test_removes_placeholders(self):
        result = relational_query_to_retrieval_text("Entity#1 works at Entity#2")
        assert "Entity#1" not in result
        assert "Entity#2" not in result
        assert "works at" in result

    def test_handles_semicolons(self):
        result = relational_query_to_retrieval_text("A; B; C")
        assert "A" in result
        assert "B" in result
        assert ";" not in result
