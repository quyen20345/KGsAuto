"""
Vector Fetching with Blocking

Fetches vectors from storage and applies blocking strategy.
"""

from __future__ import annotations
from ..config import RunConfig
from ..storage.entity_store_adapter import build_vector_store
from .llm_blocking_strategy import LLMBlockingStrategy
from .primary_type_blocking import PrimaryTypeBlockingStrategy


def fetch_and_block_vectors(
    config: RunConfig,
    use_llm_blocking: bool = True,
) -> dict[str, list[dict]]:
    """
    Fetch vectors from storage and apply blocking strategy.

    Args:
        config: Run configuration
        use_llm_blocking: If True, use LLM-based blocking; else use hard-coded primary_type

    Returns:
        dict mapping block_id → list of items in that block
    """
    # Fetch from storage
    store = build_vector_store(
        backend=config.store_backend,
        collection_name=config.resolve_collection_name(),
        vector_dim=config.embedding_dim,
        qdrant_url=config.qdrant_url,
    )
    items = store.fetch_embeddings()

    # Apply blocking strategy (always enabled)
    if use_llm_blocking:
        # LLM-based blocking
        strategy = LLMBlockingStrategy(
            llm_provider=config.llm_provider,
            llm_model=config.llm_model,
            llm_api_key=config.llm_api_key,
        )
    else:
        # Hard-coded primary_type blocking (fallback)
        strategy = PrimaryTypeBlockingStrategy()

    blocks = strategy.block(items)
    return blocks
