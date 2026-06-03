from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from apps.pipeline_api.core.neo4j_vector import Neo4jVectorService


class Neo4jVectorStore:
    """Vector store adapter backed by Neo4j Vector Index."""

    def __init__(self, neo4j_service: Neo4jVectorService) -> None:
        self._svc = neo4j_service

    def upsert_embeddings(self, embedded_nodes: list[dict[str, Any]]) -> int:
        return self._svc.upsert_embeddings(embedded_nodes)

    def fetch_embeddings(self) -> list[dict[str, Any]]:
        return self._svc.fetch_all_embeddings()

    def search_similar(
        self,
        vector: list[float],
        top_k: int = 5,
        min_score: float = 0.85,
    ) -> list[dict[str, Any]]:
        return self._svc.search_similar(vector, top_k=top_k, min_score=min_score)

    def fetch_embeddings_by_ids(self, node_ids: list[str]) -> list[dict[str, Any]]:
        return self._svc.fetch_embeddings_by_ids(node_ids)
