from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_START_KEYS = ("source", "start_id", "start", "startNode", "from")
_END_KEYS = ("target", "end_id", "end", "endNode", "to")
_ENDPOINT_KEYS = set(_START_KEYS) | set(_END_KEYS)


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
    entities: dict[str, dict[str, Any]] = {}
    for _fname, data in kg_files.items():
        for node in data.get("nodes", []):
            node_id = str(node.get("id", "")).strip()
            if not node_id:
                continue
            entities[node_id] = {
                "labels": list(node.get("labels", [])),
                "properties": dict(node.get("properties", {})),
                "merged_ids": [],
            }
    return entities


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

        new_rels: list[dict[str, Any]] = []
        seen_edges: set[tuple[str, str, str]] = set()
        for rel in data.get("relationships", []):
            raw_start = _resolve_endpoint(rel, _START_KEYS)
            raw_end = _resolve_endpoint(rel, _END_KEYS)
            start = canonical_map.get(raw_start, raw_start)
            end = canonical_map.get(raw_end, raw_end)
            rel_type = str(rel.get("type", "RELATED_TO"))

            if not start or not end or start == end:
                continue

            key = (start, rel_type, end)
            if key in seen_edges:
                continue
            seen_edges.add(key)

            rel_props = dict(rel.get("properties", {}))
            for rk, rv in rel.items():
                if rk in _ENDPOINT_KEYS or rk in {"id", "type", "properties"}:
                    continue
                rel_props[rk] = rv

            new_rels.append(
                {
                    "id": rel.get("id") or f"rel_{start}_{rel_type}_{end}",
                    "type": rel_type,
                    "source": start,
                    "target": end,
                    "properties": rel_props,
                }
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
            }
        )

    return stats
