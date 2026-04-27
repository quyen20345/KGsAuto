from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..types import NodeRecord
from ..utils.canonical_name_selector import select_canonical_name


def load_kg_files(input_dir: Path) -> dict[str, dict[str, Any]]:
    files: dict[str, dict[str, Any]] = {}
    for path in sorted(input_dir.glob("*.json")):
        with open(path, "r", encoding="utf-8") as f:
            files[path.name] = json.load(f)
    return files


def extract_node_records(kg_files: dict[str, dict[str, Any]]) -> list[NodeRecord]:
    """
    Extract node records from KG files with deduplication and property merging.

    For nodes with same ID appearing in multiple files:
    - Merge properties (union for lists, fill missing for scalars)
    - Keep first source_file encountered
    - Embed only once
    """
    merged_nodes: dict[str, NodeRecord] = {}

    for source_file, data in kg_files.items():
        for node in data.get("nodes", []):
            node_id = str(node.get("id", "")).strip()
            if not node_id:
                continue

            labels = [str(x) for x in node.get("labels", []) if x]
            properties = dict(node.get("properties", {}))

            if node_id not in merged_nodes:
                # First occurrence: create new record
                merged_nodes[node_id] = NodeRecord(
                    node_id=node_id,
                    labels=labels,
                    properties=properties,
                    source_file=source_file,
                )
            else:
                # Subsequent occurrence: merge properties
                existing = merged_nodes[node_id]

                # Merge labels (union)
                for label in labels:
                    if label not in existing.labels:
                        existing.labels.append(label)

                # Merge properties
                for key, val in properties.items():
                    # Skip empty values
                    if val is None or val == "" or val == []:
                        continue

                    existing_val = existing.properties.get(key)

                    if key == "name":
                        old_name = existing_val if isinstance(existing_val, str) else ""
                        new_names = val if isinstance(val, list) else [val]
                        aliases = existing.properties.get("aliases", [])
                        alias_candidates = aliases if isinstance(aliases, list) else [aliases]
                        candidates = [old_name, *new_names, *alias_candidates]
                        preferred_names = [old_name, *new_names]
                        existing.properties["name"] = select_canonical_name(candidates, preferred_names)

                    elif key == "description":
                        # Merge descriptions into list
                        old_desc = existing_val if isinstance(existing_val, list) else ([] if existing_val is None else [existing_val])
                        new_desc = val if isinstance(val, list) else [val]

                        # Union and deduplicate
                        merged_desc = list(set(old_desc + new_desc))
                        existing.properties["description"] = merged_desc

                    elif key == "aliases":
                        # Union aliases
                        old_aliases = existing_val if isinstance(existing_val, list) else ([] if existing_val is None else [existing_val])
                        new_aliases = val if isinstance(val, list) else [val]

                        # Merge and deduplicate
                        merged_aliases = list(set(old_aliases + new_aliases))
                        existing.properties["aliases"] = merged_aliases

                    elif existing_val is None or existing_val == "" or existing_val == []:
                        # Fill missing field
                        existing.properties[key] = val

                    elif isinstance(existing_val, list) and isinstance(val, list):
                        # Union lists
                        merged_list = list(set(existing_val + val))
                        existing.properties[key] = merged_list

                    # For other scalars: keep existing value (first occurrence wins)

    return list(merged_nodes.values())
