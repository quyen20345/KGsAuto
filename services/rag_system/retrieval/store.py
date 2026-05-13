"""Qdrant chunk storage adapter."""

import uuid
from typing import Any, Dict, List

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer
from tqdm import tqdm


class Store:
    """Store and search embedded document chunks in Qdrant."""

    _embedder_cache: dict[tuple[str, str], SentenceTransformer] = {}

    def __init__(self, config):
        self.config = config
        self.client = QdrantClient(url=config.qdrant_url)
        self.collection_name = config.markdown_collection
        self.embedder = self._get_embedder(config.embedding_model, getattr(config, "embedding_device", "cpu"))

    @classmethod
    def _get_embedder(cls, model_name: str, device: str = "cpu"):
        cache_key = (model_name, device)
        if cache_key not in cls._embedder_cache:
            cls._embedder_cache[cache_key] = SentenceTransformer(model_name, device=device)
        return cls._embedder_cache[cache_key]

    def create_collection(self):
        collections = self.client.get_collections().collections
        if any(c.name == self.collection_name for c in collections):
            print(f"Collection '{self.collection_name}' already exists")
            return

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=self.config.embedding_dim, distance=Distance.COSINE),
        )
        print(f"✓ Created collection: {self.collection_name}")

    def delete_collection(self):
        try:
            self.client.delete_collection(collection_name=self.collection_name)
            print(f"✓ Deleted collection: {self.collection_name}")
        except Exception as e:
            print(f"✗ Failed to delete collection: {e}")

    def upsert_chunks(self, chunks: List[Dict[str, Any]], show_progress: bool = True) -> int:
        if not chunks:
            return 0

        texts = [chunk["text"] for chunk in chunks]
        print(f"Generating embeddings for {len(texts)} chunks...")
        embeddings = self.embedder.encode(
            texts,
            batch_size=self.config.embedding_batch_size,
            show_progress_bar=show_progress,
        )

        points = []
        for chunk, embedding in zip(chunks, embeddings):
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk["chunk_id"]))
            points.append(PointStruct(id=point_id, vector=embedding.tolist(), payload=chunk))

        batch_size = 1000
        total_batches = (len(points) + batch_size - 1) // batch_size

        print(f"Upserting {len(points)} points in {total_batches} batches...")
        for i in tqdm(range(0, len(points), batch_size), disable=not show_progress):
            batch = points[i : i + batch_size]
            self.client.upsert(collection_name=self.collection_name, points=batch)

        print(f"✓ Upserted {len(points)} chunks to Qdrant")
        return len(points)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        query_embedding = self.embedder.encode(query)

        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding.tolist(),
            limit=top_k,
            with_payload=True,
        )

        chunks = []
        for point in response.points:
            chunk = point.payload.copy()
            chunk["score"] = point.score
            chunks.append(chunk)

        return chunks

    def count(self) -> int:
        try:
            collection_info = self.client.get_collection(collection_name=self.collection_name)
            return collection_info.points_count
        except Exception:
            return 0

    def collection_exists(self) -> bool:
        collections = self.client.get_collections().collections
        return any(c.name == self.collection_name for c in collections)
