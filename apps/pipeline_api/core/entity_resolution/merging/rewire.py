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


def _relationship_type_clause(rel_type: str) -> str:
    from apps.pipeline_api.core.neo4j_vector import escape_identifier, sanitize_label

    return f"`{escape_identifier(sanitize_label(rel_type or 'RELATED_TO'))}`"


def canonicalize_relationships(
    relationships: list[dict[str, Any]],
    canonical_map: dict[str, str],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    flat_map = flatten_canonical_map(canonical_map)
    out: list[dict[str, Any]] = []
    self_loops_removed = 0
    rewired = 0
    for rel in relationships:
        raw_start = _resolve_endpoint(rel, _START_KEYS)
        raw_end = _resolve_endpoint(rel, _END_KEYS)
        start = flat_map.get(raw_start, raw_start)
        end = flat_map.get(raw_end, raw_end)
        if not start or not end or start == end:
            self_loops_removed += 1
            continue
        if start != raw_start or end != raw_end:
            rewired += 1
        out.append(_build_relationship_payload(rel, start, end, str(rel.get("type") or "RELATED_TO")))
    deduped, relationships_deduplicated, duplicate_groups = _deduplicate_relationships(out)
    return deduped, {
        "relationships_rewired": rewired,
        "self_loops_removed": self_loops_removed,
        "relationships_deduplicated": relationships_deduplicated,
        "duplicate_relationship_groups": duplicate_groups,
    }


def _merge_existing_node_into_canonical(tx, old_id: str, canonical_id: str) -> dict[str, int]:
    if old_id == canonical_id:
        return {"nodes_deleted": 0, "relationships_rewired": 0}

    old_exists = tx.run(
        "MATCH (old:KGEntity {id: $old_id}) RETURN count(old) AS total",
        old_id=old_id,
    ).single()
    canonical_exists = tx.run(
        "MATCH (canonical:KGEntity {id: $canonical_id}) RETURN count(canonical) AS total",
        canonical_id=canonical_id,
    ).single()
    if not old_exists or not old_exists["total"] or not canonical_exists or not canonical_exists["total"]:
        return {"nodes_deleted": 0, "relationships_rewired": 0}

    rewired = 0
    outgoing = tx.run(
        """
        MATCH (old:KGEntity {id: $old_id})-[r]->(target)
        RETURN type(r) AS rel_type, properties(r) AS props, target.id AS target_id
        """,
        old_id=old_id,
    )
    for row in outgoing:
        target_id = row["target_id"]
        if not target_id or target_id == canonical_id:
            continue
        rel_type = _relationship_type_clause(row["rel_type"])
        tx.run(
            f"""
            MATCH (canonical:KGEntity {{id: $canonical_id}}), (target {{id: $target_id}})
            MERGE (canonical)-[r:{rel_type}]->(target)
            SET r += $props
            """,
            canonical_id=canonical_id,
            target_id=target_id,
            props=dict(row["props"] or {}),
        ).consume()
        rewired += 1

    incoming = tx.run(
        """
        MATCH (source)-[r]->(old:KGEntity {id: $old_id})
        RETURN type(r) AS rel_type, properties(r) AS props, source.id AS source_id
        """,
        old_id=old_id,
    )
    for row in incoming:
        source_id = row["source_id"]
        if not source_id or source_id == canonical_id:
            continue
        rel_type = _relationship_type_clause(row["rel_type"])
        tx.run(
            f"""
            MATCH (source {{id: $source_id}}), (canonical:KGEntity {{id: $canonical_id}})
            MERGE (source)-[r:{rel_type}]->(canonical)
            SET r += $props
            """,
            source_id=source_id,
            canonical_id=canonical_id,
            props=dict(row["props"] or {}),
        ).consume()
        rewired += 1

    tx.run("MATCH (old:KGEntity {id: $old_id}) DETACH DELETE old", old_id=old_id).consume()
    return {"nodes_deleted": 1, "relationships_rewired": rewired}


def rewire_graph_neo4j(
    driver,
    canonical_map: dict[str, str],
    canonical_overrides: dict[str, dict[str, Any]],
    neo4j_vector_service,
    relationships: list[dict[str, Any]] | None = None,
    embedding_items: list[dict[str, Any]] | None = None,
) -> dict[str, int]:
    from apps.pipeline_api.core.neo4j_vector import clean_neo4j_properties

    relationships = relationships or []
    embedding_items = embedding_items or []
    stats = {
        "nodes_created": 0,
        "nodes_updated": 0,
        "nodes_deleted": 0,
        "relationships_created": 0,
        "relationships_rewired": 0,
        "relationships_deduplicated": 0,
        "self_loops_removed": 0,
        "embeddings_updated": 0,
    }

    existing_ids: set[str] = set()
    canonical_ids = sorted(canonical_overrides)
    if canonical_ids:
        with driver.session() as session:
            rows = session.run(
                "MATCH (n:KGEntity) WHERE n.id IN $ids RETURN n.id AS id",
                ids=canonical_ids,
            )
            existing_ids = {str(row["id"]) for row in rows}

    if embedding_items:
        stats["embeddings_updated"] = neo4j_vector_service.upsert_embeddings(embedding_items)
        for item in embedding_items:
            if str(item.get("node_id")) in existing_ids:
                stats["nodes_updated"] += 1
            else:
                stats["nodes_created"] += 1

    with driver.session() as session:
        for canonical_id, override in canonical_overrides.items():
            if any(str(item.get("node_id")) == canonical_id for item in embedding_items):
                continue
            props = clean_neo4j_properties(dict(override.get("properties") or {}))
            props["id"] = canonical_id
            session.run(
                "MERGE (n:KGEntity {id: $id}) SET n += $props",
                id=canonical_id,
                props=props,
            ).consume()
            if canonical_id in existing_ids:
                stats["nodes_updated"] += 1
            else:
                stats["nodes_created"] += 1

    canonical_map = flatten_canonical_map(canonical_map)
    with driver.session() as session:
        for old_id, canonical_id in sorted(canonical_map.items()):
            if old_id == canonical_id:
                continue
            tx_stats = session.execute_write(_merge_existing_node_into_canonical, old_id, canonical_id)
            stats["nodes_deleted"] += tx_stats.get("nodes_deleted", 0)
            stats["relationships_rewired"] += tx_stats.get("relationships_rewired", 0)

    canonical_relationships, rel_stats = canonicalize_relationships(relationships, canonical_map)
    stats["relationships_rewired"] += rel_stats["relationships_rewired"]
    stats["self_loops_removed"] += rel_stats["self_loops_removed"]
    stats["relationships_deduplicated"] += rel_stats["relationships_deduplicated"]

    with driver.session() as session:
        for rel in canonical_relationships:
            rel_type = _relationship_type_clause(rel.get("type") or "RELATED_TO")
            props = clean_neo4j_properties(dict(rel.get("properties") or {}))
            if rel.get("id"):
                props.setdefault("id", rel.get("id"))
            row = session.run(
                f"""
                MATCH (source {{id: $source_id}}), (target {{id: $target_id}})
                MERGE (source)-[r:{rel_type}]->(target)
                ON CREATE SET r = $props, r.created_count = 1
                ON MATCH SET r += $props, r.created_count = coalesce(r.created_count, 1) + 1
                RETURN r.created_count AS created_count
                """,
                source_id=rel["source"],
                target_id=rel["target"],
                props=props,
            ).single()
            if row and row["created_count"] == 1:
                stats["relationships_created"] += 1

        self_loop_row = session.run("MATCH (n)-[r]->(n) DELETE r RETURN count(r) AS total").single()
        if self_loop_row:
            stats["self_loops_removed"] += int(self_loop_row["total"] or 0)

    return stats
