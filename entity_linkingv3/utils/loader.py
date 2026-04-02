from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_kg_files(kg_dir: str | Path) -> dict[str, dict[str, Any]]:
    kg_dir = Path(kg_dir)
    files: dict[str, dict[str, Any]] = {}
    for path in sorted(kg_dir.glob("*.json")):
        with open(path, "r", encoding="utf-8") as f:
            files[path.name] = json.load(f)
    return files


def collect_entities_from_kg_files(kg_files: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}

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
                    "id": entity_id,
                    "labels": list(node.get("labels", [])),
                    "properties": dict(node.get("properties", {})),
                }

    return list(seen.values())
