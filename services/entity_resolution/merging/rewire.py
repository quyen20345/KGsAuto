from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from collections import defaultdict

from ..preprocessing.normalize import normalize_aliases

logger = logging.getLogger(__name__)

_START_KEYS = ("source", "start_id", "start", "startNode", "from")
_END_KEYS = ("target", "end_id", "end", "endNode", "to")
_ENDPOINT_KEYS = set(_START_KEYS) | set(_END_KEYS)


def _build_relationship_payload(rel: dict[str, Any], start: str, end: str, rel_type: str) -> dict[str, Any]:
    rel_props = dict(rel.get("properties", {}))
    for rk, rv in rel.items():
        if rk in _ENDPOINT_KEYS or rk in {"id", "type", "properties"}:
            continue
        rel_props[rk] = rv

    return {
        "id": rel.get("id"),
        "type": rel_type,
        "source": start,
        "target": end,
        "properties": rel_props,
    }


def _merge_relationship_properties(base_props: dict[str, Any], merge_props: dict[str, Any]) -> dict[str, Any]:
    """
    Merge properties from duplicate relationships.

    Strategy:
    - Scalar properties: Keep first non-null value
    - List properties: Concatenate and deduplicate
    - Conflicting values: Keep first, log warning
    """
    merged = dict(base_props)

    for key, val in merge_props.items():
        if val is None or val == "" or val == []:
            continue

        existing_val = merged.get(key)

        # If key doesn't exist or is empty, use new value
        if existing_val is None or existing_val == "" or existing_val == []:
            merged[key] = val
        # Both are lists: concatenate and deduplicate
        elif isinstance(existing_val, list) and isinstance(val, list):
            merged[key] = list(set(existing_val + val))
        # Conflicting scalar values: keep first, log warning
        elif existing_val != val:
            logger.warning(
                f"Property conflict for key '{key}': keeping '{existing_val}', ignoring '{val}'"
            )

    return merged


def _deduplicate_relationships(relationships: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int, int]:
    """
    Deduplicate relationships with identical (source, target, type).

    Returns:
        - Deduplicated relationship list
        - Number of relationships removed
        - Number of duplicate groups found
    """
    # Group by (source, target, type) tuple
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)

    for rel in relationships:
        key = (rel["source"], rel["target"], rel["type"])
        groups[key].append(rel)

    deduplicated: list[dict[str, Any]] = []
    relationships_removed = 0
    duplicate_groups = 0

    for key, group in groups.items():
        if len(group) == 1:
            # No duplicates, keep as-is
            deduplicated.append(group[0])
        else:
            # Duplicates found: merge into first relationship
            duplicate_groups += 1
            relationships_removed += len(group) - 1

            canonical = group[0]
            merged_ids = [canonical["id"]]
            merged_props = dict(canonical.get("properties", {}))

            # Merge properties from duplicates
            for dup in group[1:]:
                merged_ids.append(dup["id"])
                dup_props = dup.get("properties", {})
                merged_props = _merge_relationship_properties(merged_props, dup_props)

            # Add merge metadata
            merged_props["merged_from_ids"] = merged_ids
            merged_props["merge_count"] = len(group)

            canonical["properties"] = merged_props
            deduplicated.append(canonical)

            logger.info(
                f"Merged {len(group)} duplicate relationships: "
                f"{key[0]} -[{key[2]}]-> {key[1]} (IDs: {merged_ids})"
            )

    return deduplicated, relationships_removed, duplicate_groups


def flatten_canonical_map(canonical_map: dict[str, str]) -> dict[str, str]:
    out = dict(canonical_map)
    for k in list(out):
        root = k
        seen = set()
        while out.get(root, root) != root:
            if root in seen:
                break
            seen.add(root)
            root = out[root]
        out[k] = root
    return out


def _resolve_endpoint(rel: dict[str, Any], keys: tuple[str, ...]) -> str:
    for k in keys:
        v = rel.get(k)
        if v:
            return str(v)
    return ""


class InlineEntityStore:
    def __init__(self, entities: dict[str, dict[str, Any]], overrides: dict[str, dict[str, Any]] | None = None) -> None:
        self.entities = entities
        self.overrides = overrides or {}

    def get_entity_by_id(self, entity_id: str) -> dict[str, Any] | None:
        if entity_id in self.overrides:
            payload = self.overrides[entity_id]
            return {
                "entity_id": entity_id,
                "labels": payload.get("labels", []),
                "properties": payload.get("properties", {}),
                "merged_ids": payload.get("merged_ids", []),
            }

        payload = self.entities.get(entity_id)
        if not payload:
            return None
        return {
            "entity_id": entity_id,
            "labels": payload.get("labels", []),
            "properties": payload.get("properties", {}),
            "merged_ids": payload.get("merged_ids", []),
        }


def load_kg_files(input_dir: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for path in sorted(input_dir.glob("*.json")):
        with open(path, "r", encoding="utf-8") as f:
            out[path.name] = json.load(f)
    return out


def collect_entities(kg_files: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """
    Collect entities from KG files with deduplication and property merging.

    For nodes with same ID appearing in multiple files:
    - Merge properties (union for lists, fill missing for scalars)
    - Merge labels (union)
    """
    entities: dict[str, dict[str, Any]] = {}

    for _fname, data in kg_files.items():
        for node in data.get("nodes", []):
            node_id = str(node.get("id", "")).strip()
            if not node_id:
                continue

            labels = list(node.get("labels", []))
            properties = dict(node.get("properties", {}))
            if "aliases" in properties:
                properties["aliases"] = normalize_aliases(properties.get("aliases"))

            if node_id not in entities:
                entities[node_id] = {
                    "labels": labels,
                    "properties": properties,
                    "merged_ids": [],
                }
            else:
                existing = entities[node_id]

                for label in labels:
                    if label not in existing["labels"]:
                        existing["labels"].append(label)

                for key, val in properties.items():
                    if val is None or val == "" or val == []:
                        continue

                    existing_val = existing["properties"].get(key)

                    if key == "aliases":
                        old_aliases = existing_val if isinstance(existing_val, list) else ([] if existing_val is None else [existing_val])
                        new_aliases = val if isinstance(val, list) else [val]
                        existing["properties"][key] = normalize_aliases(old_aliases + new_aliases)
                    elif existing_val is None or existing_val == "" or existing_val == []:
                        existing["properties"][key] = val
                    elif isinstance(existing_val, list) and isinstance(val, list):
                        existing["properties"][key] = list(set(existing_val + val))

    return entities


def _filter_relationships(
    relationships: list[dict[str, Any]],
    canonical_map: dict[str, str],
    valid_node_ids: set[str],
) -> tuple[list[dict[str, Any]], int, int, int]:
    filtered_relationships: list[dict[str, Any]] = []
    dangling_removed = 0

    for rel in relationships:
        raw_start = _resolve_endpoint(rel, _START_KEYS)
        raw_end = _resolve_endpoint(rel, _END_KEYS)
        start = canonical_map.get(raw_start, raw_start)
        end = canonical_map.get(raw_end, raw_end)
        rel_type = str(rel.get("type", "RELATED_TO"))

        if not start or not end or start == end:
            dangling_removed += 1
            continue

        if start not in valid_node_ids or end not in valid_node_ids:
            dangling_removed += 1
            continue

        filtered_relationships.append(_build_relationship_payload(rel, start, end, rel_type))

    # Deduplicate relationships after filtering
    deduplicated_rels, rels_removed, duplicate_groups = _deduplicate_relationships(filtered_relationships)

    return deduplicated_rels, dangling_removed, rels_removed, duplicate_groups


def rewire_graph(
    input_dir: Path,
    output_dir: Path,
    canonical_map: dict[str, str],
    canonical_overrides: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    kg_files = load_kg_files(input_dir)
    entities = collect_entities(kg_files)
    store = InlineEntityStore(entities, overrides=canonical_overrides)
    output_dir.mkdir(parents=True, exist_ok=True)

    canonical_map = flatten_canonical_map(canonical_map)
    stats: list[dict[str, Any]] = []

    for filename, data in kg_files.items():
        new_nodes: list[dict[str, Any]] = []
        seen_nodes: set[str] = set()

        for node in data.get("nodes", []):
            node_id = str(node.get("id", ""))
            if not node_id:
                continue

            canonical_id = canonical_map.get(node_id, node_id)
            if canonical_id in seen_nodes:
                continue
            seen_nodes.add(canonical_id)

            payload = store.get_entity_by_id(canonical_id)
            if payload:
                new_nodes.append(
                    {
                        "id": canonical_id,
                        "labels": payload.get("labels", node.get("labels", [])),
                        "properties": payload.get("properties", node.get("properties", {})),
                    }
                )
            else:
                new_nodes.append(
                    {
                        "id": canonical_id,
                        "labels": node.get("labels", []),
                        "properties": node.get("properties", {}),
                    }
                )

        valid_node_ids = {node["id"] for node in new_nodes if node.get("id")}
        new_rels, dangling_removed, rels_deduplicated, duplicate_groups = _filter_relationships(
            data.get("relationships", []),
            canonical_map,
            valid_node_ids,
        )

        with open(output_dir / filename, "w", encoding="utf-8") as f:
            json.dump({"nodes": new_nodes, "relationships": new_rels}, f, ensure_ascii=False, indent=2)

        stats.append(
            {
                "file": filename,
                "nodes_before": len(data.get("nodes", [])),
                "nodes_after": len(new_nodes),
                "rels_before": len(data.get("relationships", [])),
                "rels_after": len(new_rels),
                "dangling_relationships_removed": dangling_removed,
                "relationships_deduplicated": rels_deduplicated,
                "duplicate_groups": duplicate_groups,
            }
        )

    return stats
