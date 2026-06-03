from __future__ import annotations

import re
from typing import Any

from apps.pipeline_api.config import EMBEDDING_DIM, EMBEDDING_MODEL, VECTOR_INDEX_NAME
from apps.pipeline_api.core.entity_resolution.preprocessing.normalize import (
    build_embedding_text,
    normalize_properties,
)
from apps.pipeline_api.core.entity_resolution.preprocessing.representation import create_embedding

LABEL_SAFE_RE = re.compile(r"[^A-Za-z0-9_]")


def sanitize_label(label: str) -> str:
    out = LABEL_SAFE_RE.sub("_", str(label or "").strip())
    if not out:
        return "Entity"
    if out[0].isdigit():
        out = "L_" + out
    return out


def escape_identifier(value: str) -> str:
    return str(value).replace("`", "``")


def _label_clause(labels: list[str]) -> str:
    normalized = []
    for label in labels:
        safe = sanitize_label(label)
        if safe not in normalized:
            normalized.append(safe)
    if "KGEntity" not in normalized:
        normalized.append("KGEntity")
    return ":".join(f"`{escape_identifier(label)}`" for label in normalized)


def _is_neo4j_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def clean_neo4j_properties(properties: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in dict(properties or {}).items():
        if key == "embedding":
            continue
        if _is_neo4j_scalar(value):
            cleaned[key] = value
        elif isinstance(value, list):
            scalar_values = [item for item in value if _is_neo4j_scalar(item)]
            cleaned[key] = scalar_values
    return cleaned


class Neo4jVectorService:
    """Neo4j Vector Index helper for KG entity embeddings."""

    def __init__(
        self,
        driver,
        index_name: str = VECTOR_INDEX_NAME,
        embedding_model: str = EMBEDDING_MODEL,
        vector_dim: int = EMBEDDING_DIM,
    ) -> None:
        self.driver = driver
        self.index_name = index_name
        self.embedding_model = embedding_model
        self.vector_dim = vector_dim

    def ensure_index(self) -> None:
        index = escape_identifier(self.index_name)
        with self.driver.session() as session:
            session.run(
                f"""
                CREATE VECTOR INDEX `{index}` IF NOT EXISTS
                FOR (n:KGEntity) ON (n.embedding)
                OPTIONS {{indexConfig: {{
                  `vector.dimensions`: $vector_dim,
                  `vector.similarity_function`: 'cosine'
                }}}}
                """,
                vector_dim=self.vector_dim,
            ).consume()

    def build_entity_embedding_text(self, labels: list[str], properties: dict[str, Any]) -> str:
        props = normalize_properties(properties or {})
        return build_embedding_text(labels or [], props)

    def embed_text(self, text: str) -> list[float]:
        return create_embedding(
            text,
            method="semantic",
            model_name=self.embedding_model,
            dim=self.vector_dim,
        )

    def embed_entity(self, labels: list[str], properties: dict[str, Any]) -> tuple[str, list[float]]:
        text = self.build_entity_embedding_text(labels, properties)
        return text, self.embed_text(text)

    def upsert_embeddings(self, items: list[dict[str, Any]]) -> int:
        if not items:
            return 0
        self.ensure_index()
        total = 0
        with self.driver.session() as session:
            for item in items:
                node_id = str(item.get("node_id") or "").strip()
                vector = item.get("vector") or []
                if not node_id or not vector:
                    continue

                payload = dict(item.get("payload") or {})
                props = clean_neo4j_properties(payload.get("properties") or payload)
                props["id"] = node_id
                labels = list(payload.get("labels") or item.get("labels") or [])
                label_clause = _label_clause(labels)
                session.run(
                    f"""
                    MERGE (n:KGEntity {{id: $node_id}})
                    SET n += $props,
                        n.embedding = $vector
                    SET n:{label_clause}
                    """,
                    node_id=node_id,
                    props=props,
                    vector=vector,
                ).consume()
                total += 1
        return total

    def search_similar(
        self,
        vector: list[float],
        top_k: int = 5,
        min_score: float = 0.85,
    ) -> list[dict[str, Any]]:
        if not vector or top_k <= 0:
            return []
        self.ensure_index()
        with self.driver.session() as session:
            rows = session.run(
                """
                CALL db.index.vector.queryNodes($index_name, $top_k, $vector)
                YIELD node, score
                WHERE score >= $min_score
                RETURN node.id AS node_id,
                       score,
                       labels(node) AS labels,
                       properties(node) AS properties
                ORDER BY score DESC
                """,
                index_name=self.index_name,
                top_k=int(top_k),
                vector=vector,
                min_score=float(min_score),
            )
            return [self._row_to_item(row, include_score=True) for row in rows if row.get("node_id")]

    def fetch_all_embeddings(self) -> list[dict[str, Any]]:
        with self.driver.session() as session:
            rows = session.run(
                """
                MATCH (n:KGEntity)
                WHERE n.id IS NOT NULL AND n.embedding IS NOT NULL
                RETURN n.id AS node_id,
                       labels(n) AS labels,
                       properties(n) AS properties
                """
            )
            return [self._row_to_item(row) for row in rows if row.get("node_id")]

    def fetch_embeddings_by_ids(self, node_ids: list[str]) -> list[dict[str, Any]]:
        ids = sorted({str(node_id) for node_id in node_ids if node_id})
        if not ids:
            return []
        with self.driver.session() as session:
            rows = session.run(
                """
                MATCH (n:KGEntity)
                WHERE n.id IN $node_ids AND n.embedding IS NOT NULL
                RETURN n.id AS node_id,
                       labels(n) AS labels,
                       properties(n) AS properties
                """,
                node_ids=ids,
            )
            return [self._row_to_item(row) for row in rows if row.get("node_id")]

    def delete_embeddings(self, node_ids: list[str]) -> int:
        ids = sorted({str(node_id) for node_id in node_ids if node_id})
        if not ids:
            return 0
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (n:KGEntity)
                WHERE n.id IN $node_ids
                REMOVE n.embedding
                RETURN count(n) AS total
                """,
                node_ids=ids,
            ).single()
            return int(result["total"] if result else 0)

    def update_embedding(self, node_id: str, new_name: str | None = None) -> None:
        with self.driver.session() as session:
            row = session.run(
                """
                MATCH (n:KGEntity {id: $node_id})
                RETURN labels(n) AS labels, properties(n) AS properties
                """,
                node_id=node_id,
            ).single()
            if not row:
                return
            labels = list(row["labels"] or [])
            properties = dict(row["properties"] or {})
            if new_name:
                properties["name"] = new_name
            text, vector = self.embed_entity(labels, properties)
            session.run(
                """
                MATCH (n:KGEntity {id: $node_id})
                SET n.embedding = $vector,
                    n.embedding_text = $embedding_text
                """,
                node_id=node_id,
                vector=vector,
                embedding_text=text,
            ).consume()

    @staticmethod
    def _row_to_item(row: Any, include_score: bool = False) -> dict[str, Any]:
        props = dict(row["properties"] or {})
        vector = list(props.pop("embedding", []) or [])
        node_id = str(row["node_id"])
        payload = {
            "node_id": node_id,
            "labels": list(row["labels"] or []),
            "primary_type": _primary_type(row["labels"] or []),
            "source_file": "neo4j",
            "properties": clean_neo4j_properties(props),
            "is_existing": True,
        }
        item = {"node_id": node_id, "vector": vector, "payload": payload}
        if include_score:
            item["score"] = float(row["score"])
        return item


def _primary_type(labels: list[str]) -> str:
    upper = [str(label).upper() for label in labels]
    if "PERSON" in upper:
        return "PERSON"
    if "ORGANIZATION" in upper:
        return "ORGANIZATION"
    if upper:
        return upper[0]
    return "UNKNOWN"
