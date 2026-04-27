"""Markdown retrieval"""

from typing import List, Dict, Any

from services.rag_system.storage import DocumentStore


class MarkdownRetriever:
    """Retrieve relevant markdown chunks using semantic search"""

    def __init__(self, config):
        self.config = config

    def retrieve(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        if top_k is None:
            top_k = self.config.top_k_markdown

        store = DocumentStore(self.config)

        if not store.collection_exists():
            print(f"Warning: Collection '{self.config.markdown_collection}' does not exist")
            print("Please run 'python -m services.rag_system.cli index' first")
            return []

        return store.search(query, top_k=top_k)

    def retrieve_by_doc_id(self, doc_id: str, top_k: int = None) -> List[Dict[str, Any]]:
        if top_k is None:
            top_k = self.config.top_k_markdown

        store = DocumentStore(self.config)
        chunks = store.search(doc_id, top_k=top_k)
        return [c for c in chunks if c.get('doc_id') == doc_id]
