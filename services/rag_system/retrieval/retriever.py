"""Semantic retrieval over indexed chunks."""

from typing import Any, Dict, List

from services.rag_system.retrieval.store import Store


class Retriever:
    """Retrieve relevant chunks using semantic search."""

    def __init__(self, config):
        self.config = config
        self._store = None

    def _get_store(self) -> Store:
        if self._store is None:
            self._store = Store(self.config)
        return self._store

    def retrieve(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        if top_k is None:
            top_k = self.config.top_k_markdown

        store = self._get_store()

        if not store.collection_exists():
            print(f"Warning: Collection '{self.config.markdown_collection}' does not exist")
            print("Please run 'python -m services.rag_system.cli index' first")
            return []

        return store.search(query, top_k=top_k)
