from __future__ import annotations

from ..config import RunConfig
from ..storage.entity_store_adapter import build_vector_store


def fetch_stage_vectors(config: RunConfig) -> list[dict]:
    store = build_vector_store(
        backend=config.store_backend,
        collection_name=config.resolve_collection_name(),
        vector_dim=config.embedding_dim,
        qdrant_url=config.qdrant_url,
    )
    return store.fetch_embeddings()
