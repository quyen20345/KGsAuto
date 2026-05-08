"""
Tests for relationship deduplication in entity resolution pipeline.
"""
import json
from pathlib import Path
import pytest

from services.entity_resolution.merging.rewire import (
    _deduplicate_relationships,
    _merge_relationship_properties,
    collect_entities,
    rewire_graph,
)


def test_merge_relationship_properties_scalars():
    """Test merging scalar properties."""
    base = {"prop1": "value1", "prop2": "value2"}
    merge = {"prop2": "different", "prop3": "value3"}

    result = _merge_relationship_properties(base, merge)

    assert result["prop1"] == "value1"
    assert result["prop2"] == "value2"  # Keep first value
    assert result["prop3"] == "value3"



def test_merge_relationship_properties_lists():
    """Test merging list properties."""
    base = {"tags": ["tag1", "tag2"]}
    merge = {"tags": ["tag2", "tag3"]}

    result = _merge_relationship_properties(base, merge)

    assert set(result["tags"]) == {"tag1", "tag2", "tag3"}



def test_merge_relationship_properties_empty_values():
    """Test handling of empty/null values."""
    base = {"prop1": "value1", "prop2": None}
    merge = {"prop2": "value2", "prop3": ""}

    result = _merge_relationship_properties(base, merge)

    assert result["prop1"] == "value1"
    assert result["prop2"] == "value2"  # Fill empty value
    assert "prop3" not in result  # Empty string ignored



def test_deduplicate_relationships_no_duplicates():
    """Test deduplication with no duplicates."""
    relationships = [
        {"id": "r1", "source": "n1", "target": "n2", "type": "KNOWS", "properties": {}},
        {"id": "r2", "source": "n1", "target": "n3", "type": "KNOWS", "properties": {}},
        {"id": "r3", "source": "n2", "target": "n3", "type": "WORKS_WITH", "properties": {}},
    ]

    deduplicated, removed, groups = _deduplicate_relationships(relationships)

    assert len(deduplicated) == 3
    assert removed == 0
    assert groups == 0



def test_deduplicate_relationships_with_duplicates():
    """Test deduplication with duplicate relationships."""
    relationships = [
        {"id": "r1", "source": "n1", "target": "n2", "type": "KNOWS", "properties": {"since": "2020"}},
        {"id": "r2", "source": "n1", "target": "n2", "type": "KNOWS", "properties": {"since": "2021"}},
        {"id": "r3", "source": "n1", "target": "n2", "type": "KNOWS", "properties": {"context": "work"}},
    ]

    deduplicated, removed, groups = _deduplicate_relationships(relationships)

    assert len(deduplicated) == 1
    assert removed == 2
    assert groups == 1

    merged_rel = deduplicated[0]
    assert merged_rel["id"] == "r1"
    assert merged_rel["source"] == "n1"
    assert merged_rel["target"] == "n2"
    assert merged_rel["type"] == "KNOWS"

    props = merged_rel["properties"]
    assert props["since"] == "2020"
    assert props["context"] == "work"
    assert props["merged_from_ids"] == ["r1", "r2", "r3"]
    assert props["merge_count"] == 3



def test_deduplicate_relationships_different_types():
    """Test that different relationship types are NOT deduplicated."""
    relationships = [
        {"id": "r1", "source": "n1", "target": "n2", "type": "KNOWS", "properties": {}},
        {"id": "r2", "source": "n1", "target": "n2", "type": "WORKS_WITH", "properties": {}},
    ]

    deduplicated, removed, groups = _deduplicate_relationships(relationships)

    assert len(deduplicated) == 2
    assert removed == 0
    assert groups == 0



def test_deduplicate_relationships_different_directions():
    """Test that different directions are treated as different relationships."""
    relationships = [
        {"id": "r1", "source": "n1", "target": "n2", "type": "KNOWS", "properties": {}},
        {"id": "r2", "source": "n2", "target": "n1", "type": "KNOWS", "properties": {}},
    ]

    deduplicated, removed, groups = _deduplicate_relationships(relationships)

    assert len(deduplicated) == 2
    assert removed == 0
    assert groups == 0



def test_rewire_graph_with_deduplication(tmp_path: Path):
    """Test full rewire_graph with relationship deduplication."""
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    test_graph = {
        "nodes": [
            {"id": "n1", "labels": ["Person"], "properties": {"name": "Alice"}},
            {"id": "n2", "labels": ["Person"], "properties": {"name": "Alice"}},
            {"id": "n3", "labels": ["Person"], "properties": {"name": "Bob"}},
        ],
        "relationships": [
            {"id": "r1", "source": "n1", "target": "n3", "type": "KNOWS", "properties": {"since": "2020"}},
            {"id": "r2", "source": "n2", "target": "n3", "type": "KNOWS", "properties": {"context": "work"}},
            {"id": "r3", "source": "n1", "target": "n3", "type": "WORKS_WITH", "properties": {}},
        ]
    }

    with open(input_dir / "test.json", "w", encoding="utf-8") as f:
        json.dump(test_graph, f)

    canonical_map = {"n2": "n1"}

    output_dir = tmp_path / "output"
    stats = rewire_graph(input_dir, output_dir, canonical_map)

    assert len(stats) == 1
    file_stats = stats[0]
    assert file_stats["nodes_before"] == 3
    assert file_stats["nodes_after"] == 2
    assert file_stats["rels_before"] == 3
    assert file_stats["rels_after"] == 2
    assert file_stats["relationships_deduplicated"] == 1
    assert file_stats["duplicate_groups"] == 1

    with open(output_dir / "test.json", "r", encoding="utf-8") as f:
        output_graph = json.load(f)

    assert len(output_graph["nodes"]) == 2
    assert len(output_graph["relationships"]) == 2

    knows_rels = [r for r in output_graph["relationships"] if r["type"] == "KNOWS"]
    assert len(knows_rels) == 1

    merged_rel = knows_rels[0]
    assert merged_rel["source"] == "n1"
    assert merged_rel["target"] == "n3"
    assert "merged_from_ids" in merged_rel["properties"]
    assert merged_rel["properties"]["merge_count"] == 2
    assert merged_rel["properties"]["since"] == "2020"
    assert merged_rel["properties"]["context"] == "work"



def test_rewire_graph_no_duplicates(tmp_path: Path):
    """Test rewire_graph with no duplicate relationships."""
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    test_graph = {
        "nodes": [
            {"id": "n1", "labels": ["Person"], "properties": {"name": "Alice"}},
            {"id": "n2", "labels": ["Person"], "properties": {"name": "Bob"}},
        ],
        "relationships": [
            {"id": "r1", "source": "n1", "target": "n2", "type": "KNOWS", "properties": {}},
        ]
    }

    with open(input_dir / "test.json", "w", encoding="utf-8") as f:
        json.dump(test_graph, f)

    output_dir = tmp_path / "output"
    stats = rewire_graph(input_dir, output_dir, canonical_map={})

    assert stats[0]["relationships_deduplicated"] == 0
    assert stats[0]["duplicate_groups"] == 0



def test_collect_entities_normalizes_whitespace_only_alias_duplicates():
    kg_files = {
        "a.json": {
            "nodes": [
                {
                    "id": "n1",
                    "labels": ["Organization"],
                    "properties": {
                        "name": "University of Engineering and Technology",
                        "aliases": ["UET"],
                    },
                }
            ],
            "relationships": [],
        },
        "b.json": {
            "nodes": [
                {
                    "id": "n1",
                    "labels": ["Organization"],
                    "properties": {
                        "name": "University of Engineering and Technology",
                        "aliases": [" UET "],
                    },
                }
            ],
            "relationships": [],
        },
    }

    entities = collect_entities(kg_files)

    assert entities["n1"]["properties"]["aliases"] == ["UET"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
