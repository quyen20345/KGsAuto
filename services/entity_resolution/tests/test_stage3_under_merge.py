"""
Regression test for Stage3 under-merge issue.

Tests that Stage3 produces actual merges when Stage2 identifies duplicates.
"""
import json
from pathlib import Path
import pytest

from services.entity_resolution.config import RunConfig
from services.entity_resolution.pipelines.stage1_pipeline import run_stage1
from services.entity_resolution.pipelines.stage2_pipeline import run_stage2
from services.entity_resolution.pipelines.stage3_pipeline import run_stage3


def test_stage3_produces_merges_for_baseline_duplicates(tmp_path: Path):
    """
    Regression test: Stage3 should produce merges for baseline duplicate data.

    Baseline data contains:
    - "Tran Huu Quyen" in 2 documents (clear duplicate)
    - "VNU-UET" / "University of Engineering and Technology" in 2 documents
    - "Knowledge Graph" / "Knowledge Graph Engineering" in 2 documents
    """
    cfg = RunConfig(
        input_dir=Path("data/baseline_mock_data"),
        artifacts_dir=tmp_path,
        run_id="test_under_merge_fix",
        store_backend="memory",
        embedding_dim=64,
        cluster_similarity_threshold=0.60,
        conservative_merge_threshold=0.88,
        enable_conservative_fallback=True,
    )

    # Run full pipeline
    s1 = run_stage1(cfg)
    s2 = run_stage2(cfg)
    s3 = run_stage3(cfg)

    # Load results
    with open(s3.id_remap_path, "r", encoding="utf-8") as f:
        id_remap = json.load(f)

    with open(s3.rewire_audit_path, "r", encoding="utf-8") as f:
        audit = json.load(f)

    with open(s3.decisions_path, "r", encoding="utf-8") as f:
        decisions = json.load(f)

    # Assertions
    assert len(id_remap) > 0, "Expected non-empty id_remap for duplicate data"

    assert audit["effective_merges_total"] > 0, "Expected effective_merges_total > 0"

    # Should have some MERGE decisions (not all SKIP_SINGLETON)
    merge_decisions = [d for d in decisions if d.get("decision") == "MERGE"]
    assert len(merge_decisions) > 0, "Expected at least one MERGE decision"

    # Singleton rate should be reasonable (not 100%)
    total_decisions = len(decisions)
    singleton_decisions = [d for d in decisions if d.get("decision") == "SKIP_SINGLETON"]
    singleton_rate = len(singleton_decisions) / total_decisions if total_decisions > 0 else 1.0

    assert singleton_rate < 0.9, f"Singleton rate too high: {singleton_rate:.2%}"

    print(f"✓ id_remap entries: {len(id_remap)}")
    print(f"✓ effective_merges_total: {audit['effective_merges_total']}")
    print(f"✓ MERGE decisions: {len(merge_decisions)}")
    print(f"✓ Singleton rate: {singleton_rate:.2%}")


def test_mdg_rejects_all_singleton_for_duplicates():
    """Test that MDG validator rejects all-singleton for multi-entity input."""
    from services.entity_resolution.evaluation.mdg_validator import MDGValidator

    validator = MDGValidator()

    # Simulate: 3 entities, all separated (suspicious)
    clustering_result = {
        "groups": [
            {"group_id": "g0", "node_ids": ["node_1"]},
            {"group_id": "g1", "node_ids": ["node_2"]},
            {"group_id": "g2", "node_ids": ["node_3"]},
        ]
    }

    embeddings = {
        "node_1": [0.5] * 64,
        "node_2": [0.51] * 64,  # Similar to node_1
        "node_3": [0.1] * 64,
    }

    is_valid, reason = validator.validate_clustering(clustering_result, embeddings)

    assert is_valid is False, "MDG should reject all-singleton for multi-entity input"
    assert "suspicious" in reason.lower()


def test_conservative_fallback_produces_merges():
    """Test that conservative fallback produces merges for high-similarity pairs."""
    from services.entity_resolution.matching.llm_cer import LLMClusterer

    clusterer = LLMClusterer("mock", "mock-model")

    # Two very similar entities from different documents
    record_set = [
        {
            "node_id": "node_person_1",
            "payload": {
                "properties": {
                    "name": "Tran Huu Quyen",
                    "aliases": ["T. H. Quyen"],
                    "source_document_id": "doc_001",
                }
            }
        },
        {
            "node_id": "node_person_2",
            "payload": {
                "properties": {
                    "name": "Tran Huu Quyen",
                    "aliases": ["Tran H. Quyen"],
                    "source_document_id": "doc_002",
                }
            }
        },
    ]

    # Very high similarity (same person)
    embeddings = {
        "node_person_1": [0.9] * 64,
        "node_person_2": [0.91] * 64,
    }

    result = clusterer._build_conservative_fallback(record_set, embeddings, 0.88)

    # Should merge into 1 group
    assert len(result["groups"]) == 1
    assert len(result["groups"][0]["node_ids"]) == 2
    assert set(result["groups"][0]["node_ids"]) == {"node_person_1", "node_person_2"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
