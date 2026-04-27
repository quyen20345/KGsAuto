"""Hybrid retrieval"""

from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any


def _score(value) -> float:
    return float(value or 0.0)


def _normalize_scores(items: list[dict[str, Any]]) -> list[float]:
    scores = [_score(item.get("score")) for item in items]
    max_score = max(scores, default=0.0)
    if max_score <= 0:
        return [1.0 / (index + 1) for index in range(len(items))]
    return [score / max_score for score in scores]

from services.rag_system.retrieval.markdown import MarkdownRetriever
from services.rag_system.retrieval.graph import GraphRetriever


class HybridRetriever:
    """Combine markdown and graph retrieval"""

    def __init__(self, config):
        self.config = config
        self.markdown_retriever = MarkdownRetriever(config)
        self.graph_retriever = GraphRetriever(config)

    def retrieve(self, query: str, top_k_markdown: int = None, top_k_graph: int = None) -> Dict[str, Any]:
        with ThreadPoolExecutor(max_workers=2) as executor:
            markdown_future = executor.submit(self.markdown_retriever.retrieve, query, top_k_markdown)
            graph_future = executor.submit(self.graph_retriever.retrieve, query, top_k_graph)
            markdown_chunks = markdown_future.result()
            graph_facts = graph_future.result()

        seen_chunk_ids = set()
        deduped_chunks = []
        for chunk in markdown_chunks:
            chunk_id = chunk.get("chunk_id") or chunk.get("id") or chunk.get("text", "")
            if chunk_id in seen_chunk_ids:
                continue
            seen_chunk_ids.add(chunk_id)
            deduped_chunks.append(chunk)

        seen_fact_keys = set()
        deduped_facts = []
        for fact in graph_facts:
            fact_key = (
                fact.get("entity_id"),
                fact.get("fact_type"),
                fact.get("fact_text"),
            )
            if fact_key in seen_fact_keys:
                continue
            seen_fact_keys.add(fact_key)
            deduped_facts.append(fact)

        merged_context = {
            "markdown_chunks": deduped_chunks,
            "graph_facts": deduped_facts,
            "ranked_items": self._rank_items(deduped_chunks, deduped_facts),
        }

        return {
            "markdown_chunks": deduped_chunks,
            "graph_facts": deduped_facts,
            "merged_context": merged_context,
        }

    def _rank_items(self, markdown_chunks: list[dict[str, Any]], graph_facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        strategy = getattr(self.config, "fusion_strategy", "weighted")
        if strategy == "rrf":
            ranked = []
            for rank, chunk in enumerate(markdown_chunks, 1):
                ranked.append(self._ranked_item("markdown", chunk, 1 / (60 + rank)))
            for rank, fact in enumerate(graph_facts, 1):
                ranked.append(self._ranked_item("graph", fact, 1 / (60 + rank)))
            return sorted(ranked, key=self._sort_key)

        markdown_weight = getattr(self.config, "markdown_weight", 0.5)
        graph_weight = getattr(self.config, "graph_weight", 0.5)
        ranked = []
        for chunk, score in zip(markdown_chunks, _normalize_scores(markdown_chunks)):
            ranked.append(self._ranked_item("markdown", chunk, score * markdown_weight))
        for fact, score in zip(graph_facts, _normalize_scores(graph_facts)):
            ranked.append(self._ranked_item("graph", fact, score * graph_weight))
        return sorted(ranked, key=lambda item: (-item["score"], item["source"], item["id"]))

    def _ranked_item(self, source: str, item: dict[str, Any], score: float) -> dict[str, Any]:
        if source == "markdown":
            item_id = item.get("chunk_id") or item.get("id") or item.get("text", "")
        else:
            item_id = item.get("entity_id") or item.get("fact_text") or item.get("id", "")
        return {
            "source": source,
            "id": str(item_id),
            "score": score,
            "item": item,
        }

    def _sort_key(self, item: dict[str, Any]):
        source_order = 0 if item["source"] == "markdown" else 1
        return -item["score"], source_order, item["id"]
