from __future__ import annotations

import logging

from services.entity_resolution.merging.merge_engine import build_id_remap_from_proposals


def test_merge_engine_skips_singleton_and_logs_warning(caplog) -> None:
    proposals = [
        {
            "proposal_id": "p_single",
            "cluster_id": "person_0001",
            "node_ids": ["node_A"],
            "canonical_id": "node_A",
        }
    ]

    with caplog.at_level(logging.WARNING):
        remap = build_id_remap_from_proposals(proposals)

    assert remap == {}
    assert any("Singleton proposal passed to merge engine" in r.message for r in caplog.records)


def test_merge_engine_maps_non_singleton_nodes() -> None:
    proposals = [
        {
            "proposal_id": "p_merge",
            "cluster_id": "person_0000",
            "node_ids": ["node_A", "node_B", "node_C"],
            "canonical_id": "node_A",
        }
    ]

    remap = build_id_remap_from_proposals(proposals)

    assert remap == {
        "node_B": "node_A",
        "node_C": "node_A",
    }
