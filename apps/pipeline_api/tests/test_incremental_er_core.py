from apps.pipeline_api.core.entity_resolution.blocking.vector_fetch import fetch_incremental_candidates
from apps.pipeline_api.core.entity_resolution.merging.rewire import canonicalize_relationships
from apps.pipeline_api.core.neo4j_vector import clean_neo4j_properties


class FakeNeo4jStore:
    def __init__(self):
        self.hits = {
            "node_new": [
                {
                    "node_id": "node_existing",
                    "vector": [0.2, 0.8],
                    "payload": {
                        "labels": ["ORGANIZATION"],
                        "properties": {"name": "Existing"},
                    },
                    "score": 0.93,
                },
                {
                    "node_id": "node_existing",
                    "vector": [0.2, 0.8],
                    "payload": {"labels": ["ORGANIZATION"], "properties": {"name": "Existing"}},
                    "score": 0.91,
                },
            ]
        }

    def search_similar(self, vector, top_k=5, min_score=0.85):
        assert vector == [1.0, 0.0]
        return self.hits["node_new"]


def test_fetch_incremental_candidates_dedupes_existing_hits():
    new_item = {
        "node_id": "node_new",
        "vector": [1.0, 0.0],
        "payload": {
            "labels": ["ORGANIZATION"],
            "properties": {"name": "New"},
            "is_existing": False,
        },
    }

    combined, candidate_map = fetch_incremental_candidates(
        FakeNeo4jStore(),
        new_records=[],
        new_embeddings=[new_item],
        top_k=5,
        min_score=0.85,
    )

    assert candidate_map == {"node_new": ["node_existing"]}
    assert sorted(item["node_id"] for item in combined) == ["node_existing", "node_new"]
    existing = next(item for item in combined if item["node_id"] == "node_existing")
    assert existing["payload"]["is_existing"] is True


def test_canonicalize_relationships_remaps_removes_self_loops_and_dedupes():
    relationships = [
        {"id": "r1", "type": "HAS_UNIT", "source": "a", "target": "b", "properties": {"p": "x"}},
        {"id": "r2", "type": "HAS_UNIT", "source": "alias_a", "target": "b", "properties": {"q": "y"}},
        {"id": "r3", "type": "RELATED_TO", "source": "alias_a", "target": "a", "properties": {}},
    ]

    remapped, stats = canonicalize_relationships(relationships, {"alias_a": "a"})

    assert len(remapped) == 1
    assert remapped[0]["source"] == "a"
    assert remapped[0]["target"] == "b"
    assert stats["relationships_rewired"] == 1
    assert stats["self_loops_removed"] == 1
    assert stats["relationships_deduplicated"] == 1


def test_clean_neo4j_properties_removes_embedding_and_unsupported_values():
    cleaned = clean_neo4j_properties({
        "id": "node_a",
        "embedding": [0.1, 0.2],
        "aliases": ["A", "B"],
        "nested": {"bad": True},
        "mixed": ["ok", {"bad": True}, 3],
    })

    assert cleaned == {"id": "node_a", "aliases": ["A", "B"], "mixed": ["ok", 3]}
