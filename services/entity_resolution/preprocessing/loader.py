from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..types import NodeRecord


def load_kg_files(input_dir: Path) -> dict[str, dict[str, Any]]:
    files: dict[str, dict[str, Any]] = {}
    for path in sorted(input_dir.glob("*.json")):
        with open(path, "r", encoding="utf-8") as f:
            files[path.name] = json.load(f)
    return files


def extract_node_records(kg_files: dict[str, dict[str, Any]]) -> list[NodeRecord]:
    records: list[NodeRecord] = []
    for source_file, data in kg_files.items():
        for node in data.get("nodes", []):
            node_id = str(node.get("id", "")).strip()
            if not node_id:
                continue

            labels = [str(x) for x in node.get("labels", []) if x]
            properties = dict(node.get("properties", {}))

            records.append(
                NodeRecord(
                    node_id=node_id,
                    labels=labels,
                    properties=properties,
                    source_file=source_file,
                )
            )
    return records
