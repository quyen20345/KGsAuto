from __future__ import annotations
from typing import Any

from entity_linkingv3.core.pairing import PairItem
from entity_linkingv3.core.merging import merge_properties, UnionFind

from ..storage.entity_store import EntityDB

def build_pair_suggestion(pair: PairItem) -> dict[str, Any]:
    seed_props = pair.seed.get("properties", {})
    candidate_props = pair.candidate.get("properties", {})
    merged_props = merge_properties(seed_props, candidate_props)

    labels = list(pair.seed.get("labels", []))
    for label in pair.candidate.get("labels", []):
        if label not in labels:
            labels.append(label)

    return {
        "canonical_id": pair.seed.get("entity_id"),
        "labels": labels,
        "merged_properties": merged_props,
    }


def build_merge_plan(merged_pairs: list[PairItem], store: EntityDB) -> dict[str, dict[str, Any]]:
    if not merged_pairs:
        return {}

    uf = UnionFind()

    for pair in merged_pairs:
        sid = pair.seed.get("entity_id")
        cid = pair.candidate.get("entity_id")
        canonical = pair.canonical_id or sid
        absorbed = cid if canonical == sid else sid
        uf.union(canonical, absorbed)

    groups: dict[str, set[str]] = {}
    for node in uf.all_nodes():
        root = uf.find(node)
        groups.setdefault(root, set()).add(node)

    plan: dict[str, dict[str, Any]] = {}
    for canonical_id, members in groups.items():
        absorbed = sorted([m for m in members if m != canonical_id])

        merged_props: dict[str, Any] = {}
        merged_labels: list[str] = []

        for entity_id in [canonical_id] + absorbed:
            payload = store.get_entity_by_id(entity_id)
            if not payload:
                continue
            merged_props = merge_properties(merged_props, payload.get("properties", {}))
            for label in payload.get("labels", []):
                if label not in merged_labels:
                    merged_labels.append(label)

        # Human override from reviewed pair decisions wins.
        for pair in merged_pairs:
            sid = pair.seed.get("entity_id")
            cid = pair.candidate.get("entity_id")
            if uf.find(sid) != canonical_id or uf.find(cid) != canonical_id:
                continue
            if pair.merged_properties:
                merged_props.update(pair.merged_properties)

        plan[canonical_id] = {
            "absorbed": absorbed,
            "properties": merged_props,
            "labels": merged_labels,
        }

    return plan


def apply_merge_plan(
    store: EntityDB,
    plan: dict[str, dict[str, Any]],
    canonical_map: dict[str, str],
) -> int:
    if not plan:
        return 0

    all_absorbed: list[str] = []

    for canonical_id, entry in plan.items():
        absorbed = entry.get("absorbed", [])
        final_props = entry.get("properties", {})
        final_labels = entry.get("labels", [])

        current = store.get_entity_by_id(canonical_id)
        if current is not None:
            existing_merged_ids = list(current.get("merged_ids", []))
        else:
            existing_merged_ids = []

        updated_entity = {
            "id": canonical_id,
            "labels": final_labels,
            "properties": final_props,
            "merged_ids": existing_merged_ids + absorbed,
        }
        store.upsert_entities([updated_entity])

        for absorbed_id in absorbed:
            canonical_map[absorbed_id] = canonical_id
        all_absorbed.extend(absorbed)

    if all_absorbed:
        store.delete_entities(all_absorbed)

    return len(plan)
