from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)


def build_cluster_groups(assignments: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Build cluster groups from stage2 assignments."""
    groups: dict[str, list[str]] = defaultdict(list)
    for row in assignments:
        cluster_id = row.get("cluster_id")
        node_id = row.get("node_id")
        if not cluster_id or not node_id or cluster_id == "noise":
            continue
        groups[str(cluster_id)].append(str(node_id))
    return groups


def build_id_remap_from_proposals(approved_proposals: list[dict[str, Any]]) -> dict[str, str]:
    remap: dict[str, str] = {}
    for proposal in approved_proposals:
        canonical_id = str(proposal.get("canonical_id", "")).strip()
        node_ids = [str(x) for x in proposal.get("node_ids", []) if str(x).strip()]
        if not canonical_id or not node_ids:
            continue

        if len(node_ids) <= 1:
            logger.warning(
                "Singleton proposal passed to merge engine: proposal_id=%s cluster_id=%s canonical_id=%s",
                proposal.get("proposal_id"),
                proposal.get("cluster_id"),
                canonical_id,
            )
            continue

        if canonical_id not in node_ids:
            canonical_id = node_ids[0]

        for node_id in node_ids:
            if node_id != canonical_id:
                remap[node_id] = canonical_id

    return remap
