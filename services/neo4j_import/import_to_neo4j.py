#!/usr/bin/env python3
import argparse
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase

from services.config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER

LABEL_SAFE_RE = re.compile(r"[^A-Za-z0-9_]")
IDENTIFIER_SPLIT_RE = re.compile(r"[_\-/\\.]+")
WHITESPACE_RE = re.compile(r"\s+")


def normalize_search_text(value: Any) -> str:
    text = WHITESPACE_RE.sub(" ", str(value or "")).strip().lower()
    text = text.replace("đ", "d")
    decomposed = unicodedata.normalize("NFD", text)
    without_marks = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return WHITESPACE_RE.sub(" ", without_marks).strip()


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def split_identifier_variants(value: Any) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    split_text = WHITESPACE_RE.sub(" ", IDENTIFIER_SPLIT_RE.sub(" ", text)).strip()
    parts = [part for part in split_text.split() if len(part) >= 2]
    variants = [text]
    if split_text and split_text != text:
        variants.append(split_text)
    variants.extend(parts)
    return list(dict.fromkeys(variants))


def build_node_search_properties(props: dict[str, Any], labels: list[str]) -> dict[str, Any]:
    name = props.get("name")
    aliases = as_list(props.get("aliases"))
    descriptions = as_list(props.get("description"))
    alias_variants: list[str] = []
    for alias in aliases:
        alias_variants.extend(split_identifier_variants(alias))

    search_parts = [name, *labels, *aliases, *alias_variants, *descriptions]
    normalized_parts = [normalize_search_text(part) for part in search_parts]
    return {
        "search_name": normalize_search_text(name),
        "search_aliases": [normalize_search_text(alias) for alias in alias_variants or aliases if normalize_search_text(alias)],
        "search_description": [normalize_search_text(desc) for desc in descriptions if normalize_search_text(desc)],
        "search_text": " ".join(dict.fromkeys(part for part in normalized_parts if part)),
    }


def build_relationship_search_properties(rel_type: str, props: dict[str, Any]) -> dict[str, Any]:
    descriptions = as_list(props.get("description"))
    type_variants = split_identifier_variants(rel_type)
    search_parts = [rel_type, *type_variants, *descriptions]
    normalized_parts = [normalize_search_text(part) for part in search_parts]
    return {
        "search_type": normalize_search_text(rel_type),
        "search_description": [normalize_search_text(desc) for desc in descriptions if normalize_search_text(desc)],
        "search_text": " ".join(dict.fromkeys(part for part in normalized_parts if part)),
    }


def sanitize_label(label: str) -> str:
    l = LABEL_SAFE_RE.sub("_", label)
    if not l:
        return "Label"
    if l[0].isdigit():
        l = "L_" + l
    return l


class KGImporter:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def create_search_indexes(self):
        with self.driver.session() as session:
            session.run(
                """
                CREATE FULLTEXT INDEX kg_entity_search IF NOT EXISTS
                FOR (n:KGEntity)
                ON EACH [n.name, n.search_name, n.search_text]
                """
            )

    def import_nodes(self, nodes, source_file):
        with self.driver.session() as session:
            for node in nodes:
                node_id = node.get("id")
                labels = node.get("labels", []) or []
                labels = [sanitize_label(l) for l in labels]

                props = node.get("properties", {}) or {}
                props_with_meta = dict(props)
                props_with_meta.update(build_node_search_properties(props_with_meta, labels))
                props_with_meta["id"] = node_id
                # props_with_meta["source_file"] = source_file

                # Use first label for MERGE, then add remaining labels
                if not labels:
                    labels = ["Entity"]  # Fallback label if none provided
                if "KGEntity" not in labels:
                    labels.append("KGEntity")

                primary_label = labels[0]
                remaining_labels = labels[1:] if len(labels) > 1 else []

                # MERGE on primary label + id
                cypher = f"MERGE (n:`{primary_label}` {{id: $id}}) SET n += $props"

                # Add remaining labels if any
                if remaining_labels:
                    label_clause = ":".join([f"`{l}`" for l in remaining_labels])
                    cypher += f" SET n:{label_clause}"

                session.run(cypher, id=node_id, props=props_with_meta)

    def import_relationships(self, relationships, source_file):
        with self.driver.session() as session:
            relationships_created = 0
            relationships_merged = 0

            for rel in relationships:
                rel_id = rel.get("id")
                rel_type = sanitize_label(rel.get("type", "RELATED_TO"))
                start_id = rel.get("source")
                end_id = rel.get("target")

                props = rel.get("properties", {}) or {}
                props_with_meta = dict(props)
                props_with_meta.update(build_relationship_search_properties(rel_type, props_with_meta))
                props_with_meta["id"] = rel_id
                # props_with_meta["source_file"] = source_file

                # MERGE on (source, target, type) tuple instead of id
                # This ensures only one relationship per unique tuple
                cypher = (
                    "MATCH (s {id: $start_id}), "
                    "(e {id: $end_id}) "
                    f"MERGE (s)-[r:`{rel_type}`]->(e) "
                    "ON CREATE SET r = $props, r.created_count = 1 "
                    "ON MATCH SET r += $props, r.created_count = coalesce(r.created_count, 0) + 1 "
                    "RETURN r.created_count as count"
                )

                result = session.run(
                    cypher,
                    start_id=start_id,
                    end_id=end_id,
                    props=props_with_meta,
                )

                record = result.single()
                if record and record["count"] == 1:
                    relationships_created += 1
                else:
                    relationships_merged += 1

            return relationships_created, relationships_merged


def load_json_file(path: Path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", "-d", required=True, help="Folder containing KG JSON files")
    args = ap.parse_args()

    folder = Path(args.dir)
    if not folder.exists() or not folder.is_dir():
        raise SystemExit(f"Folder not found: {folder}")

    importer = KGImporter(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    try:
        importer.create_search_indexes()
        json_files = list(folder.glob("*.json"))
        if not json_files:
            raise SystemExit("No JSON files found in folder")

        total_rels_created = 0
        total_rels_merged = 0

        for file_path in json_files:
            print(f"Importing {file_path.name} ...")
            data = load_json_file(file_path)

            nodes = data.get("nodes", [])
            relationships = data.get("relationships", [])

            importer.import_nodes(nodes, file_path.name)
            rels_created, rels_merged = importer.import_relationships(relationships, file_path.name)

            total_rels_created += rels_created
            total_rels_merged += rels_merged

            print(f"  Nodes: {len(nodes)}, Relationships: {len(relationships)} "
                  f"(created: {rels_created}, merged: {rels_merged})")

        print("\nAll files imported successfully.")
        print(f"Total relationships created: {total_rels_created}")
        print(f"Total relationships merged (duplicates): {total_rels_merged}")

    finally:
        importer.close()


if __name__ == "__main__":
    main()
