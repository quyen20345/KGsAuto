import json, os
from pathlib import Path

import torch

from entity_linkingv2.entity_store import EntityDB
from entity_linkingv2.linker import run_entity_linking


def load_kg_files(kg_dir: str) -> dict[str, dict]:
    """Load all *.json files from directory. Returns dict{filename: data}."""
    kg_dir = Path(kg_dir)
    files = {}
    for path in sorted(kg_dir.glob("*.json")):
        with open(path, "r", encoding="utf-8") as f:
            files[path.name] = json.load(f)
    return files


def collect_entities_from_kg_files(kg_files: dict[str, dict]) -> list[dict]:
    """
    Collect all unique nodes from KG files as entity dicts for EntityDB.
    If same ID appears in multiple files, merge properties and labels.
    Return a list of entity dicts with keys: id, labels, properties.
    """
    seen = {}
    for _filename, data in kg_files.items():
        for node in data.get("nodes", []):
            entity_id = node.get("id", "")
            if not entity_id:
                continue
            if entity_id in seen:
                existing = seen[entity_id]
                existing["properties"].update(node.get("properties", {}))
                for label in node.get("labels", []):
                    if label not in existing["labels"]:
                        existing["labels"].append(label)
            else:
                seen[entity_id] = {
                    "id":         entity_id,
                    "labels":     list(node.get("labels", [])),
                    "properties": dict(node.get("properties", {})),
                }
    return list(seen.values())


# ── Relationship key helpers ───────────────────────────────────────────────────
# Extractor có thể dùng nhiều tên khác nhau cho start/end node.
# FIX: thay vì hardcode "start_id"/"end_id", thử lần lượt các key phổ biến.
_START_KEYS = ("start_id", "start", "startNode", "source", "from")
_END_KEYS   = ("end_id",   "end",   "endNode",   "target", "to")
_ALL_ENDPOINT_KEYS = set(_START_KEYS) | set(_END_KEYS)


def _resolve_endpoint(rel: dict, keys: tuple) -> str:
    """Thử lần lượt các key candidates, trả về giá trị đầu tiên tìm thấy."""
    for k in keys:
        v = rel.get(k)
        if v:
            return v
    return ""


# Phase 6: Rewrite KG files
def rewrite_kg_files(
    kg_files:      dict[str, dict],
    store:         EntityDB,
    canonical_map: dict[str, str],
    output_dir:    str | Path,
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    entity_cache: dict[str, dict | None] = {}

    def get_canonical_data(entity_id: str) -> dict | None:
        """Cache miss → fetch Qdrant; hit → return cached."""
        cid = canonical_map.get(entity_id, entity_id)
        if cid not in entity_cache:
            entity_cache[cid] = store.get_entity_by_id(cid)
        return entity_cache[cid]

    _logged_rel_keys = False   # chỉ log 1 lần

    for filename, data in kg_files.items():
        # ── Rewrite nodes ──────────────────────────────────────────────────
        new_nodes: list[dict] = []
        seen_ids:  set[str]   = set()

        for node in data.get("nodes", []):
            node_id      = node.get("id", "")
            canonical_id = canonical_map.get(node_id, node_id)

            if canonical_id in seen_ids:
                continue
            seen_ids.add(canonical_id)

            qdrant_data = get_canonical_data(node_id)
            if qdrant_data:
                new_nodes.append({
                    "id":         canonical_id,
                    "labels":     qdrant_data.get("labels",     node.get("labels", [])),
                    "properties": qdrant_data.get("properties", node.get("properties", {})),
                })
            else:
                new_nodes.append({
                    "id":         node_id,
                    "labels":     node.get("labels", []),
                    "properties": node.get("properties", {}),
                })

        # ── Rewrite relationships ──────────────────────────────────────────
        new_rels:   list[dict] = []
        seen_edges: set[tuple] = set()
        rels_raw = data.get("relationships", [])

        # FIX: log key names một lần để xác nhận field đúng
        if not _logged_rel_keys and rels_raw:
            print(f"  [debug] relationship keys detected: {set(rels_raw[0].keys())}")
            _logged_rel_keys = True

        for rel in rels_raw:
            # FIX: auto-detect start/end keys thay vì hardcode "start_id"/"end_id"
            raw_start = _resolve_endpoint(rel, _START_KEYS)
            raw_end   = _resolve_endpoint(rel, _END_KEYS)

            start = canonical_map.get(raw_start, raw_start)
            end   = canonical_map.get(raw_end,   raw_end)
            rtype = rel.get("type", "")

            if not start or not end:
                continue   # bỏ qua rel không có endpoint hợp lệ

            if start == end:
                continue   # self-loop sau merge → drop

            edge_key = (start, rtype, end)
            if edge_key in seen_edges:
                continue   # duplicate edge → drop
            seen_edges.add(edge_key)

            extra = {
                k: v for k, v in rel.items()
                if k not in _ALL_ENDPOINT_KEYS and k != "type"
            }
            new_rels.append({"start_id": start, "type": rtype, "end_id": end, **extra})

        # ── Write output ───────────────────────────────────────────────────
        out_path = output_dir / filename
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"nodes": new_nodes, "relationships": new_rels},
                      f, ensure_ascii=False, indent=2)

        print(f"  {filename}: "
              f"{len(data.get('nodes', []))} nodes -> {len(new_nodes)} | "
              f"{len(data.get('relationships', []))} rels -> {len(new_rels)}")


def main():
    KG_DIR          = os.getenv("EXTRACTED_DIR",            "data/extracted_v2")
    OUTPUT_DIR      = os.getenv("LINKED_DIR",               "data/linked")
    MODEL           = os.getenv("MODEL_LINK",               "gpt-5")
    BASE_URL        = os.getenv("BASE_URL",                 "http://localhost:8317/v1")
    API_KEY         = os.getenv("PROXYPAL_KEY",             "")
    COLLECTION_NAME = os.getenv("COLLECTION_NAME",          "entities_store")
    DEVICE          = "cpu"# os.getenv("EL_DEVICE", "gpu" if torch.cuda.is_available() else "cpu")
    MAX_ITER        = int(os.getenv("MAX_ITERATIONS",       "5"))
    SCORE           = float(os.getenv("SCORE_THRESHOLD",    "0.85"))
    CROSS_SCORE     = float(os.getenv("CROSS_LABEL_THRESHOLD", "0.95"))
    LIMIT           = int(os.getenv("LIMIT",                "10"))
    MAX_WORKERS     = int(os.getenv("MAX_WORKERS",          "8"))

    print("Phase 0: Ingest")
    kg_files = load_kg_files(KG_DIR)
    print(f"Loaded {len(kg_files)} KG files from {KG_DIR}")

    entities = collect_entities_from_kg_files(kg_files)
    print(f"Collected {len(entities)} unique entities from KG files")

    store = EntityDB(collection_name=COLLECTION_NAME, device=DEVICE)
    n = store.upsert_entities(entities)
    print(f"Upserted {n} entities into Qdrant collection '{COLLECTION_NAME}'")

    print("Phase 1-5: Linking")
    canonical_map = run_entity_linking(
        store=store,
        max_iterations=MAX_ITER,
        limit=LIMIT,
        score_threshold=SCORE,
        cross_label_threshold=CROSS_SCORE,
        max_workers=MAX_WORKERS,
    )

    print("Phase 6: Rewrite KG files with canonical IDs")
    rewrite_kg_files(kg_files, store, canonical_map, OUTPUT_DIR)


if __name__ == "__main__":
    main()