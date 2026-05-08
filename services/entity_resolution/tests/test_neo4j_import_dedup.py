"""
Tests for Neo4j import relationship deduplication.

Note: These tests require a running Neo4j instance.
Set NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD in environment or .env file.
"""
import json
import os
import pytest
from pathlib import Path
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")


@pytest.fixture
def neo4j_driver():
    """Create Neo4j driver for testing."""
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    yield driver
    driver.close()


@pytest.fixture
def clean_test_db(neo4j_driver):
    """Clean test database before and after tests."""
    with neo4j_driver.session() as session:
        # Clean before test
        session.run("MATCH (n:TestNode) DETACH DELETE n")

    yield

    with neo4j_driver.session() as session:
        # Clean after test
        session.run("MATCH (n:TestNode) DETACH DELETE n")


def test_neo4j_import_deduplicates_relationships(tmp_path: Path, neo4j_driver, clean_test_db):
    """Test that Neo4j import deduplicates relationships with same (source, target, type)."""
    from services.neo4j_import.import_to_neo4j import KGImporter

    # Create test data with duplicate relationships
    test_graph = {
        "nodes": [
            {"id": "test_n1", "labels": ["TestNode"], "properties": {"name": "Alice"}},
            {"id": "test_n2", "labels": ["TestNode"], "properties": {"name": "Bob"}},
        ],
        "relationships": [
            {"id": "test_r1", "source": "test_n1", "target": "test_n2", "type": "KNOWS", "properties": {"since": "2020"}},
            {"id": "test_r2", "source": "test_n1", "target": "test_n2", "type": "KNOWS", "properties": {"context": "work"}},
            {"id": "test_r3", "source": "test_n1", "target": "test_n2", "type": "KNOWS", "properties": {"verified": True}},
        ]
    }

    # Save to file
    test_file = tmp_path / "test_graph.json"
    with open(test_file, "w", encoding="utf-8") as f:
        json.dump(test_graph, f)

    # Import to Neo4j
    importer = KGImporter(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    try:
        importer.import_nodes(test_graph["nodes"], "test_graph.json")
        created, merged = importer.import_relationships(test_graph["relationships"], "test_graph.json")

        # Should create 1 relationship and merge 2 duplicates
        assert created == 1
        assert merged == 2

    finally:
        importer.close()

    # Query Neo4j to verify only one relationship exists
    with neo4j_driver.session() as session:
        result = session.run(
            "MATCH (a:TestNode {id: 'test_n1'})-[r:KNOWS]->(b:TestNode {id: 'test_n2'}) "
            "RETURN r"
        )
        relationships = list(result)

        assert len(relationships) == 1, "Should have exactly one KNOWS relationship"

        rel = relationships[0]["r"]
        # Check that properties were merged
        assert rel["since"] == "2020"
        assert rel["context"] == "work"
        assert rel["verified"] is True
        assert rel["created_count"] == 3  # Merged 3 times


def test_neo4j_import_preserves_different_types(tmp_path: Path, neo4j_driver, clean_test_db):
    """Test that relationships with different types are NOT deduplicated."""
    from services.neo4j_import.import_to_neo4j import KGImporter

    test_graph = {
        "nodes": [
            {"id": "test_n3", "labels": ["TestNode"], "properties": {"name": "Charlie"}},
            {"id": "test_n4", "labels": ["TestNode"], "properties": {"name": "Diana"}},
        ],
        "relationships": [
            {"id": "test_r4", "source": "test_n3", "target": "test_n4", "type": "KNOWS", "properties": {}},
            {"id": "test_r5", "source": "test_n3", "target": "test_n4", "type": "WORKS_WITH", "properties": {}},
        ]
    }

    # Import to Neo4j
    importer = KGImporter(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    try:
        importer.import_nodes(test_graph["nodes"], "test_graph.json")
        created, merged = importer.import_relationships(test_graph["relationships"], "test_graph.json")

        # Should create 2 relationships (different types)
        assert created == 2
        assert merged == 0

    finally:
        importer.close()

    # Query Neo4j to verify both relationships exist
    with neo4j_driver.session() as session:
        result = session.run(
            "MATCH (a:TestNode {id: 'test_n3'})-[r]->(b:TestNode {id: 'test_n4'}) "
            "RETURN type(r) as rel_type"
        )
        rel_types = [record["rel_type"] for record in result]

        assert len(rel_types) == 2
        assert "KNOWS" in rel_types
        assert "WORKS_WITH" in rel_types


def test_neo4j_import_preserves_different_directions(tmp_path: Path, neo4j_driver, clean_test_db):
    """Test that relationships with different directions are NOT deduplicated."""
    from services.neo4j_import.import_to_neo4j import KGImporter

    test_graph = {
        "nodes": [
            {"id": "test_n5", "labels": ["TestNode"], "properties": {"name": "Eve"}},
            {"id": "test_n6", "labels": ["TestNode"], "properties": {"name": "Frank"}},
        ],
        "relationships": [
            {"id": "test_r6", "source": "test_n5", "target": "test_n6", "type": "KNOWS", "properties": {}},
            {"id": "test_r7", "source": "test_n6", "target": "test_n5", "type": "KNOWS", "properties": {}},
        ]
    }

    # Import to Neo4j
    importer = KGImporter(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    try:
        importer.import_nodes(test_graph["nodes"], "test_graph.json")
        created, merged = importer.import_relationships(test_graph["relationships"], "test_graph.json")

        # Should create 2 relationships (different directions)
        assert created == 2
        assert merged == 0

    finally:
        importer.close()

    # Query Neo4j to verify both directions exist
    with neo4j_driver.session() as session:
        result = session.run(
            "MATCH (a:TestNode {id: 'test_n5'})-[r:KNOWS]->(b:TestNode {id: 'test_n6'}) "
            "RETURN count(r) as count"
        )
        forward_count = result.single()["count"]

        result = session.run(
            "MATCH (a:TestNode {id: 'test_n6'})-[r:KNOWS]->(b:TestNode {id: 'test_n5'}) "
            "RETURN count(r) as count"
        )
        backward_count = result.single()["count"]

        assert forward_count == 1
        assert backward_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
