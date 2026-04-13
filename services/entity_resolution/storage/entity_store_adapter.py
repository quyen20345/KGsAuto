from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class VectorStore(ABC):
    @abstractmethod
    def upsert_embeddings(self, embedded_nodes: list[dict[str, Any]]) -> int:
        raise NotImplementedError

    @abstractmethod
    def fetch_embeddings(self) -> list[dict[str, Any]]:
        raise NotImplementedError


class MemoryVectorStore(VectorStore):
    _registry: dict[str, dict[str, dict[str, Any]]] = {}

    def __init__(self, collection_name: str = "memory_default") -> None:
        self.collection_name = collection_name
        MemoryVectorStore._registry.setdefault(collection_name, {})

    def upsert_embeddings(self, embedded_nodes: list[dict[str, Any]]) -> int:
        bucket = MemoryVectorStore._registry[self.collection_name]
        for item in embedded_nodes:
            bucket[item["node_id"]] = dict(item)
        return len(embedded_nodes)

    def fetch_embeddings(self) -> list[dict[str, Any]]:
        return list(MemoryVectorStore._registry[self.collection_name].values())


class QdrantVectorStore(VectorStore):
    def __init__(self, collection_name: str, vector_dim: int, url: str = "http://localhost:6333") -> None:
        from qdrant_client import QdrantClient, models

        self.collection_name = collection_name
        self.vector_dim = vector_dim
        self._models = models
        self.client = QdrantClient(url=url, timeout=300)
        if not self.client.collection_exists(collection_name):
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(size=vector_dim, distance=models.Distance.COSINE),
            )

    @staticmethod
    def _point_id(node_id: str) -> str:
        import uuid

        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"elv4:{node_id}"))

    def upsert_embeddings(self, embedded_nodes: list[dict[str, Any]]) -> int:
        models = self._models
        points: list[Any] = []
        for item in embedded_nodes:
            points.append(
                models.PointStruct(
                    id=self._point_id(item["node_id"]),
                    vector=item["vector"],
                    payload=item["payload"],
                )
            )

        # Batch upsert to avoid timeout with large datasets
        batch_size = 1000
        total_upserted = 0
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            if batch:
                self.client.upsert(collection_name=self.collection_name, points=batch, wait=True)
                total_upserted += len(batch)

        return total_upserted

    def fetch_embeddings(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        offset: Any = None
        while True:
            points, next_offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=512,
                offset=offset,
                with_payload=True,
                with_vectors=True,
            )

            for point in points:
                payload = dict(point.payload or {})
                node_id = str(payload.get("node_id", ""))
                if not node_id:
                    continue

                vector_any = point.vector
                if isinstance(vector_any, dict):
                    vector_any = next(iter(vector_any.values()), [])
                vector = list(vector_any or [])

                items.append(
                    {
                        "node_id": node_id,
                        "vector": vector,
                        "payload": payload,
                    }
                )

            if next_offset is None:
                break
            offset = next_offset

        return items


def build_vector_store(
    backend: str,
    collection_name: str,
    vector_dim: int,
    qdrant_url: str = "http://localhost:6333",
) -> VectorStore:
    backend = backend.lower()
    if backend == "memory":
        return MemoryVectorStore(collection_name=collection_name)
    if backend == "qdrant":
        return QdrantVectorStore(collection_name=collection_name, vector_dim=vector_dim, url=qdrant_url)
    raise ValueError(f"Unsupported store backend: {backend}")
