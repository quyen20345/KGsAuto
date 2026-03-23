#!/usr/bin/env python3
import json
import re
import argparse
import os
from pathlib import Path
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")

LABEL_SAFE_RE = re.compile(r"[^A-Za-z0-9_]")


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

    def ensure_constraint(self):
        cql = (
            "CREATE CONSTRAINT kg_node_id_unique IF NOT EXISTS "
            "FOR (n:KgNode) REQUIRE n.id IS UNIQUE"
        )
        with self.driver.session() as s:
            s.run(cql)

    def import_nodes(self, nodes, source_file):
        with self.driver.session() as session:
            for node in nodes:
                node_id = node.get("id")
                labels = node.get("labels", []) or []
                labels = [sanitize_label(l) for l in labels]

                props = node.get("properties", {}) or {}
                props_with_meta = dict(props)
                props_with_meta["id"] = node_id
                # props_with_meta["source_file"] = source_file

                label_clause = ":".join([f"`{l}`" for l in labels]) if labels else ""
                
                # 1. MERGE CHỈ TRÊN NHỮNG TRƯỜNG CÓ CONSTRAINT LÀ UNIQUE
                cypher = (
                    "MERGE (n:KgNode {id: $id}) "
                    "SET n += $props"
                )
                
                # 2. SAU ĐÓ MỚI SET THÊM CÁC LABEL PHỤ (Neo4j cho phép SET n:Label1:Label2)
                if label_clause:
                    cypher += f" SET n:{label_clause}"

                session.run(cypher, id=node_id, props=props_with_meta)

    def import_relationships(self, relationships, source_file):
        with self.driver.session() as session:
            for rel in relationships:
                rel_id = rel.get("id")
                rel_type = sanitize_label(rel.get("type", "RELATED_TO"))
                start_id = rel.get("start_id")
                end_id = rel.get("end_id")

                props = rel.get("properties", {}) or {}
                props_with_meta = dict(props)
                props_with_meta["id"] = rel_id
                # props_with_meta["source_file"] = source_file

                cypher = (
                    "MATCH (s:KgNode {id: $start_id}), "
                    "(e:KgNode {id: $end_id}) "
                    f"MERGE (s)-[r:`{rel_type}` {{id: $id}}]->(e) "
                    "SET r += $props"
                )

                session.run(
                    cypher,
                    start_id=start_id,
                    end_id=end_id,
                    id=rel_id,
                    props=props_with_meta,
                )


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
        importer.ensure_constraint()

        json_files = list(folder.glob("*.json"))
        if not json_files:
            raise SystemExit("No JSON files found in folder")

        for file_path in json_files:
            print(f"Importing {file_path.name} ...")
            data = load_json_file(file_path)

            nodes = data.get("nodes", [])
            relationships = data.get("relationships", [])

            importer.import_nodes(nodes, file_path.name)
            importer.import_relationships(relationships, file_path.name)

        print("All files imported successfully.")

    finally:
        importer.close()


if __name__ == "__main__":
    main()