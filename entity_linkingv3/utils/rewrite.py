from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..storage.entity_store import EntityDB


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


def rewrite_kg_files(
    kg_files: dict[str, dict[str, Any]],
    store: EntityDB,
    canonical_map: dict[str, str],
    output_dir: str | Path,
) -> list[dict[str, Any]]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    stats: list[dict[str, Any]] = []
    entity_cache: dict[str, dict[str, Any] | None] = {}

    def get_entity(entity_id: str) -> dict[str, Any] | None:
        cid = canonical_map.get(entity_id, entity_id)
        if cid not in entity_cache:
            entity_cache[cid] = store.get_entity_by_id(cid)
        return entity_cache[cid]

    for filename, data in kg_files.items():
        new_nodes: list[dict[str, Any]] = []
        seen_nodes: set[str] = set()

        for node in data.get("nodes", []):
            node_id = node.get("id", "")
            if not node_id:
                continue

            canonical_id = canonical_map.get(node_id, node_id)
            if canonical_id in seen_nodes:
                continue
            seen_nodes.add(canonical_id)

            payload = get_entity(node_id)
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
            rel_type = rel.get("type", "RELATED_TO")

            if not start or not end:
                continue
            if start == end:
                continue

            edge_key = (start, rel_type, end)
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)

            rel_props = dict(rel.get("properties", {}))
            for key, value in rel.items():
                if key in _ENDPOINT_KEYS or key in {"id", "type", "properties"}:
                    continue
                rel_props[key] = value

            rel_id = rel.get("id") or f"rel_{start}_{rel_type}_{end}"
            new_rels.append(
                {
                    "id": rel_id,
                    "type": rel_type,
                    "source": start,
                    "target": end,
                    "properties": rel_props,
                }
            )

        with open(output_path / filename, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "nodes": new_nodes,
                    "relationships": new_rels,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

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
