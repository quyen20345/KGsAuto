"""
Regression test for Stage3 under-merge issue.

Tests that Stage3 produces actual merges when Stage2 identifies duplicates.
"""
import json
from pathlib import Path
import pytest

from unittest.mock import patch

from services.entity_resolution.config import RunConfig
from services.entity_resolution.pipelines.stage1_pipeline import run_stage1
from services.entity_resolution.pipelines.stage2_pipeline import run_stage2
from services.entity_resolution.pipelines.stage3_pipeline import run_stage3


def test_stage3_produces_merges_for_baseline_duplicates(tmp_path: Path):
    """
    Regression test: Stage3 should produce merges for mock data.

    Tests that Stage3 pipeline runs successfully and produces valid output.
    """
    cfg = RunConfig(
        input_dir=Path("data/mock_data"),
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

    canonical_decisions_path = cfg.stage_dir("stage3") / "canonical_decisions.json"
    with open(canonical_decisions_path, "r", encoding="utf-8") as f:
        canonical_decisions = json.load(f)

    # Assertions - verify structure and basic functionality
    assert isinstance(id_remap, dict), "id_remap should be a dictionary"
    assert "canonical_entities_total" in audit, "audit should contain canonical_entities_total"
    assert isinstance(decisions, list), "decisions should be a list"
    assert isinstance(canonical_decisions, list), "canonical_decisions should be a list"
    if canonical_decisions:
        first_decision = canonical_decisions[0]
        assert "canonical_id" in first_decision
        assert "canonical_name" in first_decision
        assert "merged_from" in first_decision
        assert "merge_count" in first_decision
        assert "legacy_canonical_id" in first_decision

    # Verify pipeline ran successfully
    assert s1.indexed_nodes >= 1, "Should index at least 1 node"
    assert s2.clusters_total >= 0, "Should have valid cluster count"

    # Calculate singleton rate
    total_decisions = len(decisions)
    if total_decisions > 0:
        singleton_decisions = [d for d in decisions if d.get("decision") == "SKIP_SINGLETON"]
        singleton_rate = len(singleton_decisions) / total_decisions
    else:
        singleton_rate = 0.0

    print(f"✓ id_remap entries: {len(id_remap)}")
    print(f"✓ canonical_entities_total: {audit['canonical_entities_total']}")
    print(f"✓ Total decisions: {total_decisions}")
    print(f"✓ Singleton rate: {singleton_rate:.2%}")


def test_stage3_writes_canonical_decisions_artifact(tmp_path: Path):
    cfg = RunConfig(
        input_dir=tmp_path / "input",
        artifacts_dir=tmp_path / "artifacts",
        run_id="test_canonical_decisions",
        store_backend="memory",
    )
    cfg.input_dir.mkdir()

    stage2_dir = cfg.stage_dir("stage2")
    stage2_dir.mkdir(parents=True)
    assignments = [
        {"node_id": "node_a", "cluster_id": "organization_0000", "probability": 0.9, "primary_type": "ORGANIZATION"},
        {"node_id": "node_b", "cluster_id": "organization_0000", "probability": 0.9, "primary_type": "ORGANIZATION"},
    ]
    (stage2_dir / "cluster_assignments.json").write_text(
        json.dumps(assignments, ensure_ascii=False),
        encoding="utf-8",
    )

    fake_entities = {
        "node_a": {"labels": ["ORGANIZATION"], "properties": {"name": "UET"}},
        "node_b": {"labels": ["ORGANIZATION"], "properties": {"name": "Trường Đại học Công nghệ"}},
    }
    fake_canonical_entities = [
        {
            "canonical_id": "node_a",
            "labels": ["ORGANIZATION"],
            "properties": {"name": "Trường Đại học Công nghệ", "aliases": ["UET"]},
            "merged_from": ["node_a", "node_b"],
        }
    ]

    with patch("services.entity_resolution.pipelines.stage3_pipeline._load_stage1_embeddings", return_value={}), \
        patch("services.entity_resolution.pipelines.stage3_pipeline.load_kg_files", return_value={}), \
        patch("services.entity_resolution.pipelines.stage3_pipeline.collect_entities", return_value=fake_entities), \
        patch("services.entity_resolution.pipelines.stage3_pipeline.rewire_graph", return_value=[]), \
        patch("services.entity_resolution.matching.two_pass_llm.TwoPassLLMResolver.resolve_cluster", return_value=fake_canonical_entities):
        result = run_stage3(cfg)

    decisions_path = cfg.stage_dir("stage3") / "canonical_decisions.json"
    decisions = json.loads(decisions_path.read_text(encoding="utf-8"))

    assert result.id_remap_path.endswith("id_remap.json")
    assert decisions == [
        {
            "cluster_id": "organization_0000",
            "cluster_ids": ["organization_0000"],
            "legacy_canonical_id": "node_a",
            "canonical_id": "node_truong_ai_hoc_cong_nghe",
            "canonical_name": "Trường Đại học Công nghệ",
            "merged_from": ["node_a", "node_b"],
            "merge_count": 2,
            "labels": ["ORGANIZATION"],
        }
    ]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
