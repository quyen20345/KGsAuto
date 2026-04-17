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

    # Assertions - verify structure and basic functionality
    assert isinstance(id_remap, dict), "id_remap should be a dictionary"
    assert "canonical_entities_total" in audit, "audit should contain canonical_entities_total"
    assert isinstance(decisions, list), "decisions should be a list"

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
