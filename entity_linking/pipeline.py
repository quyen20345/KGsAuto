"""
Full entity linking pipeline:
  1. Load KG JSON files from a directory
  2. Collect all nodes → upsert into EntityDB (Qdrant)
  3. Run entity linking (search similar → LLM merges)
  4. Build ID remap from merged_ids → canonical ID
  5. Rewrite KG JSON files with updated nodes + remapped relationships
"""

import json
import logging
from pathlib import Path

from entity_linking.entity_store import EntityDB
from entity_linking.linker import run_entity_linking

logger = logging.getLogger(__name__)


def load_kg_files(kg_dir: str | Path) -> dict[str, dict]:
    """Load all *_kg.json files from directory. Returns {filename: data}."""
    kg_dir = Path(kg_dir)
    files = {}
    for path in sorted(kg_dir.glob("*_kg.json")):
        with open(path, "r", encoding="utf-8") as f:
            files[path.name] = json.load(f)
        logger.info("Loaded %s (%d nodes, %d rels)",
                     path.name,
                     len(files[path.name].get("nodes", [])),
                     len(files[path.name].get("relationships", [])))
    return files


def collect_entities(kg_files: dict[str, dict]) -> list[dict]:
    """Extract all unique nodes from KG files as entity dicts for EntityDB."""
    seen = {}
    for filename, data in kg_files.items():
        for node in data.get("nodes", []):
            entity_id = node.get("id", "")
            if not entity_id:
                continue
            # If same ID appears in multiple files, merge properties
            if entity_id in seen:
                existing = seen[entity_id]
                existing["properties"].update(node.get("properties", {}))
                for label in node.get("labels", []):
                    if label not in existing["labels"]:
                        existing["labels"].append(label)
            else:
                seen[entity_id] = {
                    "id": entity_id,
                    "labels": list(node.get("labels", [])),
                    "properties": dict(node.get("properties", {})),
                }
    return list(seen.values())


def build_id_remap(store: EntityDB) -> dict[str, str]:
    """
    After linking, build a mapping: old_id → canonical_id.
    Each remaining entity has merged_ids listing which IDs were absorbed.
    """
    remap = {}
    for entity_id in store.get_all_entity_ids():
        entity = store.get_entity_by_id(entity_id)
        if entity is None:
            continue
        for old_id in entity.get("merged_ids", []):
            remap[old_id] = entity_id
    return remap


def rewrite_kg_files(
    kg_files: dict[str, dict],
    store: EntityDB,
    id_remap: dict[str, str],
    output_dir: str | Path,
):
    """
    Rewrite each KG JSON file:
    - Nodes: replace merged nodes with canonical entity from store
    - Relationships: remap start_id/end_id, deduplicate
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build canonical entities lookup from store
    canonical_entities = {}
    for entity_id in store.get_all_entity_ids():
        entity = store.get_entity_by_id(entity_id)
        if entity:
            canonical_entities[entity_id] = {
                "id": entity_id,
                "labels": entity.get("labels", []),
                "properties": entity.get("properties", {}),
            }

    for filename, data in kg_files.items():
        # --- Rewrite nodes ---
        new_nodes = []
        seen_node_ids = set()
        for node in data.get("nodes", []):
            node_id = node.get("id", "")
            # Remap to canonical ID
            canonical_id = id_remap.get(node_id, node_id)

            if canonical_id in seen_node_ids:
                continue
            seen_node_ids.add(canonical_id)

            # Use canonical entity from store if available
            if canonical_id in canonical_entities:
                new_nodes.append(canonical_entities[canonical_id])
            else:
                # Entity wasn't in store (shouldn't happen), keep original
                node_copy = dict(node)
                node_copy["id"] = canonical_id
                new_nodes.append(node_copy)

        # --- Rewrite relationships ---
        new_rels = []
        seen_rels = set()
        for rel in data.get("relationships", []):
            start_id = rel.get("start_id", "")
            end_id = rel.get("end_id", "")

            # Remap IDs
            new_start = id_remap.get(start_id, start_id)
            new_end = id_remap.get(end_id, end_id)

            # Skip self-loops created by merge
            if new_start == new_end:
                logger.info("Skipping self-loop: %s -[%s]-> %s (was %s -> %s)",
                            new_start, rel.get("type"), new_end, start_id, end_id)
                continue

            # Deduplicate: same (start, type, end)
            dedup_key = (new_start, rel.get("type", ""), new_end)
            if dedup_key in seen_rels:
                continue
            seen_rels.add(dedup_key)

            new_rel = dict(rel)
            new_rel["start_id"] = new_start
            new_rel["end_id"] = new_end
            new_rels.append(new_rel)

        # --- Write output ---
        output_data = {"nodes": new_nodes, "relationships": new_rels}
        output_path = output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)

        logger.info("Wrote %s: %d nodes, %d rels",
                     filename, len(new_nodes), len(new_rels))


# def run_pipeline(
#     kg_dir: str | Path,
#     output_dir: str | Path,
#     llm,
#     collection_name: str = "entity_linking",
#     device: str = "cpu",
#     max_iterations: int = 5,
#     limit: int = 10,
#     score_threshold: float = 0.5,
# ) -> dict:
def run_pipeline(
    kg_dir: str | Path,
    output_dir: str | Path,
    llm,
    collection_name: str = "entity_linking",
    device: str = "cpu",
    max_iterations: int = 5,
    limit: int = 10,
    score_threshold: float = 0.85,
    max_workers: int = 8,
) -> dict:
    """
    Full pipeline:
      KG JSONs → EntityDB → Entity Linking → Rewrite KG JSONs
    """
    # 1. Load KG files
    kg_files = load_kg_files(kg_dir)
    if not kg_files:
        logger.warning("No KG JSON files found in %s", kg_dir)
        return {"total_merges": 0, "iterations": 0, "remaining_entities": 0}

    # 2. Collect entities and upsert into vector store
    entities = collect_entities(kg_files)
    logger.info("Collected %d unique entities from %d files", len(entities), len(kg_files))

    store = EntityDB(collection_name=collection_name, device=device)
    # store.drop_collection()  # fresh start
    # store = EntityDB(collection_name=collection_name, device=device)

    count = store.upsert_entities(entities)
    logger.info("Upserted %d entities into Qdrant", count)

    # 3. Run entity linking
    # stats = run_entity_linking(
    #     store, llm,
    #     max_iterations=max_iterations,
    #     limit=limit,
    #     score_threshold=score_threshold,
    # )
    stats = run_entity_linking(
        store, llm,
        max_iterations=max_iterations,
        limit=limit,
        score_threshold=score_threshold,
        max_workers=max_workers,
    )
    logger.info("Entity linking done: %s", stats)

    # 4. Build ID remap and rewrite files
    id_remap = build_id_remap(store)
    if id_remap:
        logger.info("ID remapping: %s", id_remap)

    rewrite_kg_files(kg_files, store, id_remap, output_dir)

    stats["id_remap"] = id_remap
    stats["files_processed"] = len(kg_files)
    return stats
