from __future__ import annotations

import json
from pathlib import Path

from services.entity_resolution.config import RunConfig
from services.entity_resolution.pipelines.stage1_pipeline import run_stage1
from services.entity_resolution.pipelines.stage2_pipeline import run_stage2
from services.entity_resolution.pipelines.stage3_pipeline import run_stage3


def test_e2e_pipeline_mock_data(tmp_path: Path) -> None:
    cfg = RunConfig(
        input_dir=Path("data/baseline_mock_data"),
        artifacts_dir=tmp_path,
        run_id="test_e2e",
        store_backend="memory",
        embedding_dim=64,
        cluster_similarity_threshold=0.60,
    )

    s1 = run_stage1(cfg)
    s2 = run_stage2(cfg)
    s3 = run_stage3(cfg)

    assert s1.indexed_nodes == 12
    assert s2.clusters_total >= 1

    with open(s3.rewire_audit_path, "r", encoding="utf-8") as f:
        audit = json.load(f)

    assert audit["run_id"] == cfg.run_id
    assert "rewrite_stats" in audit
    assert len(audit["rewrite_stats"]) == 4
    assert "singleton_skips_total" in audit
    assert "merge_decisions_total" in audit

    with open(s3.id_remap_path, "r", encoding="utf-8") as f:
        actual = json.load(f)

    # Baseline data has clear duplicates, should produce merges
    assert len(actual) > 0, "Expected merges for baseline duplicate data"

    # Verify specific expected merges
    # "Tran Huu Quyen" appears in doc_001 and doc_002
    person_nodes = [k for k in actual.keys() if "quyen" in k.lower()]
    assert len(person_nodes) >= 1, "Expected person merge"

    # "VNU-UET" / "University of Engineering and Technology"
    org_nodes = [k for k in actual.keys() if "university" in k.lower() or "uet" in k.lower()]
    assert len(org_nodes) >= 1, "Expected organization merge"
