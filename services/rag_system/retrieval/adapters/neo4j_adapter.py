"""Neo4j adapter for the unified GraphSearch runtime."""

from __future__ import annotations

import asyncio
import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable, List

CONTEXT_PATTERN = (
    r"Knowledge Graph Data \(Entity\):\s*```json\s*(.*?)\s*```.*?"
    r"Knowledge Graph Data \(Relationship\):\s*```json\s*(.*?)\s*```.*?"
    r"Document Chunks.*?```json\s*(.*?)\s*```.*?"
    r"Reference Document List.*?```(?:json|text)?\s*(.*?)\s*```"
)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _join_text(value: Any, limit: int | None = None) -> str:
    text = " ".join(str(item).strip() for item in _as_list(value) if str(item).strip())
    return text[:limit].strip() if limit else text


def _chunk_ids(properties: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for key in ("chunk_id", "chunk_ids", "source_chunk_ids"):
        for value in _as_list(properties.get(key)):
            text = str(value).strip()
            if text and text not in ids:
                ids.append(text)
    return ids


def _fold_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.lower().replace("đ", "d"))
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def _dedupe_text(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        text = " ".join(str(value).split())
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(text)
    return deduped


def _doc_id_from_chunk_id(chunk_id: str) -> str:
    doc_id, separator, _ = chunk_id.rpartition("_chunk_")
    return doc_id if separator else chunk_id


def format_graphsearch_context(
    entities: Iterable[dict[str, Any]],
    relationships: Iterable[dict[str, Any]],
    chunks: Iterable[dict[str, Any]],
    sources: Iterable[dict[str, Any]],
) -> str:
    """Format Neo4j evidence in the section layout expected by GraphSearch."""
    entities_json = json.dumps(list(entities), ensure_ascii=False, indent=2)
    relationships_json = json.dumps(list(relationships), ensure_ascii=False, indent=2)
    chunks_json = json.dumps(list(chunks), ensure_ascii=False, indent=2)
    sources_json = json.dumps(list(sources), ensure_ascii=False, indent=2)

    return f"""Knowledge Graph Data (Entity):

```json
{entities_json}
```

Knowledge Graph Data (Relationship):

```json
{relationships_json}
```

Document Chunks (Each entry has a reference_id refer to the `Reference Document List`):

```json
{chunks_json}
```

Reference Document List (Each entry starts with a [reference_id] that corresponds to entries in the Document Chunks):

```json
{sources_json}
```"""


class Neo4jAdapter:
    """Adapter to use the imported Neo4j graph with GraphSearch."""

    def __init__(self, top_k: int = 5, raw_markdown_dir: str | Path | None = None, config: Any | None = None):
        from apps.backend.app.db.neo4j import get_driver
        from services.rag_system.config import RAGConfig

        self.driver = get_driver()
        self.config = config or RAGConfig()
        self.top_k = top_k
        self.raw_markdown_dir = Path(raw_markdown_dir or os.getenv("RAG_MARKDOWN_DIR", "data/raw/uet"))
        self.keyword_extraction_mode = getattr(self.config, "graph_keyword_extraction_mode", "llm_with_fallback")
        self.keyword_max_terms = getattr(self.config, "graph_keyword_max_terms", 12)
        self.keyword_timeout_seconds = getattr(self.config, "graph_keyword_timeout_seconds", 15.0)
        self._markdown_index: dict[str, Path] | None = None

    def init_graphrag(self, working_dir: str, EMBED_MODEL):
        """No-op: graph already exists in Neo4j."""
        pass

    async def aquery_context(self, question: str) -> str:
        keywords = await self._extract_keywords_async(question)
        entities_by_id: dict[str, dict[str, Any]] = {}
        relationships_by_key: dict[str, dict[str, Any]] = {}
        chunks_by_id: dict[str, dict[str, Any]] = {}
        sources_by_id: dict[str, dict[str, Any]] = {}

        def add_chunk(chunk_id: str) -> None:
            if chunk_id in chunks_by_id:
                return
            source_path, content = self._load_markdown_chunk(chunk_id)
            if not content:
                return
            reference_id = len(sources_by_id)
            chunks_by_id[chunk_id] = {
                "chunk_id": chunk_id,
                "content": content,
                "reference_id": reference_id,
            }
            sources_by_id[chunk_id] = {
                "reference_id": reference_id,
                "source": source_path or chunk_id,
            }

        def add_entity_from_details(details: dict[str, Any] | None) -> None:
            if not details:
                return
            entity_id = details["id"]
            retrieval_score = float(details.get("score") or details.get("retrieval_score") or 0.0)
            if entity_id not in entities_by_id:
                properties = details.get("properties", {}) or {}
                entities_by_id[entity_id] = {
                    "entity_name": details.get("name") or entity_id,
                    "entity_type": ", ".join(details.get("labels") or []),
                    "description": _join_text(properties.get("description"), limit=1200),
                    "aliases": _as_list(properties.get("aliases")),
                    "source_id": entity_id,
                    "chunk_id": _chunk_ids(properties),
                    "retrieval_score": retrieval_score,
                }
                for chunk_id in _chunk_ids(properties)[:2]:
                    add_chunk(chunk_id)
            else:
                entities_by_id[entity_id]["retrieval_score"] = max(
                    float(entities_by_id[entity_id].get("retrieval_score") or 0.0),
                    retrieval_score,
                )

        def add_relationship(rel: dict[str, Any]) -> None:
            source = rel.get("source") or rel.get("source_id")
            target = rel.get("target") or rel.get("target_id")
            relation = rel.get("relation") or "RELATED_TO"
            key = f"{rel.get('source_id') or source}|{relation}|{rel.get('target_id') or target}"
            if key in relationships_by_key:
                return
            props = rel.get("rel_props", {}) or {}
            chunk_ids = _chunk_ids(props)
            relationships_by_key[key] = {
                "src_id": source,
                "tgt_id": target,
                "description": _join_text(props.get("description"), limit=1200) or f"{source} {relation} {target}",
                "keywords": relation,
                "weight": 1.0,
                "chunk_id": chunk_ids,
                "source_id": rel.get("source_id"),
                "target_id": rel.get("target_id"),
                "retrieval_score": float(rel.get("score") or rel.get("retrieval_score") or 0.0),
            }
            for chunk_id in chunk_ids[:2]:
                add_chunk(chunk_id)

        for keyword in keywords[:8]:
            for entity in self._search_entities(keyword, limit=max(3, self.top_k)):
                add_entity_from_details(self._get_entity_details(entity["id"]))
                for rel in self._get_relationships(entity["id"], limit=self.top_k * 2):
                    add_relationship(rel)
                    add_entity_from_details(self._details_from_rel(rel, "source"))
                    add_entity_from_details(self._details_from_rel(rel, "target"))

            for rel in self._search_relationships(keyword, limit=self.top_k * 2):
                add_relationship(rel)
                add_entity_from_details(self._details_from_rel(rel, "source"))
                add_entity_from_details(self._details_from_rel(rel, "target"))

        entities = sorted(entities_by_id.values(), key=lambda item: item.get("retrieval_score", 0.0), reverse=True)
        relationships = sorted(
            relationships_by_key.values(),
            key=lambda item: item.get("retrieval_score", 0.0),
            reverse=True,
        )
        return format_graphsearch_context(
            entities[: self.top_k * 2],
            relationships[: self.top_k * 3],
            list(chunks_by_id.values())[: self.top_k],
            list(sources_by_id.values())[: self.top_k],
        )

    async def aquery_answer(self, question: str) -> str:
        from services.rag_system.workflows.deep_graph_search.utils import openai_complete

        context = await self.aquery_context(question)
        prompt = f"""Based only on the following knowledge graph and document evidence, answer the question in Vietnamese.

Question: {question}

Evidence:
{context}

If the evidence is insufficient, say that the provided graph/document evidence is not enough."""

        return await openai_complete(prompt=prompt)

    def context_filter(self, context_data: str, filter_type: str) -> str:
        match = re.search(CONTEXT_PATTERN, context_data, re.DOTALL)
        if not match:
            return ""

        entities_str, relations_str, text_chunks_str, reference_list_str = match.groups()

        if filter_type == "semantic":
            return f"""Document Chunks (Each entry has a reference_id refer to the `Reference Document List`):

```json
{text_chunks_str}
```

Reference Document List (Each entry starts with a [reference_id] that corresponds to entries in the Document Chunks):

```json
{reference_list_str}
```"""

        if filter_type == "relational":
            return f"""Knowledge Graph Data (Entity):

```json
{entities_str}
```

Knowledge Graph Data (Relationship):

```json
{relations_str}
```"""

        return context_data

    async def _extract_keywords_async(self, query: str) -> List[str]:
        normalized_query = self._normalize_query(query)
        heuristic = self._extract_keywords_heuristic(normalized_query)
        mode = self.keyword_extraction_mode
        if mode == "heuristic_only":
            return heuristic[: self.keyword_max_terms]

        llm_keywords = await self._extract_llm_keywords(normalized_query)
        if not any(llm_keywords.values()):
            fallback = [] if mode == "llm_only" else heuristic[: self.keyword_max_terms]
            return fallback

        merged = self._merge_keyword_candidates(normalized_query, heuristic, llm_keywords)
        selected = merged[: self.keyword_max_terms]
        if merged or mode == "llm_only":
            return selected
        return heuristic[: self.keyword_max_terms]

    async def _extract_llm_keywords(self, query: str) -> dict[str, list[str]]:
        from services.rag_system.components.llm.components import empty_keyword_extraction, keywords_extraction

        try:
            return await asyncio.wait_for(keywords_extraction(query), timeout=self.keyword_timeout_seconds)
        except Exception:
            return empty_keyword_extraction()

    def _merge_keyword_candidates(
        self,
        normalized_query: str,
        heuristic_keywords: list[str],
        llm_keywords: dict[str, list[str]],
    ) -> list[str]:
        candidates = [
            *self._domain_priority_terms(normalized_query),
            *llm_keywords.get("must_keep_phrases", []),
            *llm_keywords.get("low_level_keywords", []),
            *llm_keywords.get("expanded_keywords", []),
            *llm_keywords.get("high_level_keywords", []),
            *heuristic_keywords,
            normalized_query.strip(),
        ]
        return _dedupe_text(candidates)

    def _extract_keywords_heuristic(self, query: str) -> List[str]:
        normalized_query = self._normalize_query(query)
        return _dedupe_text([*self._domain_priority_terms(normalized_query), *self._token_keywords(normalized_query)]) or [normalized_query.strip()]

    def _domain_priority_terms(self, query: str) -> list[str]:
        folded_query = _fold_text(query)
        role_query = any(term in folded_query for term in ("hieu truong", "rector"))
        uet_query = any(
            term in folded_query
            for term in (
                "dai hoc cong nghe",
                "dh cong nghe",
                "dhcn",
                "uet",
                "vnu-uet",
                "university of engineering and technology",
            )
        )

        priority_terms: list[str] = []
        if role_query and uet_query:
            priority_terms.extend(
                [
                    "Hiệu trưởng Trường Đại học Công nghệ",
                    "Hiệu trưởng Trường ĐH Công nghệ",
                    "Hiệu trưởng Trường ĐHCN",
                    "Ban Giám hiệu",
                ]
            )
        elif role_query:
            priority_terms.extend(["Hiệu trưởng", "Ban Giám hiệu"])
        if uet_query:
            priority_terms.extend(
                [
                    "Trường Đại học Công nghệ",
                    "Trường ĐH Công nghệ",
                    "Trường ĐHCN",
                    "UET",
                    "VNU University of Engineering and Technology",
                ]
            )
        return priority_terms

    def _token_keywords(self, query: str) -> list[str]:
        stop_words = {
            "là", "của", "các", "có", "được", "này", "đó", "cho", "và", "với",
            "ai", "gì", "nào", "trong", "theo", "một", "những", "quan", "hệ",
            "the", "of", "in", "on", "and", "or", "to", "is", "are", "was",
            "đại", "học", "công", "nghệ", "trường",
            "dai", "hoc", "cong", "nghe", "truong",
        }
        words = re.findall(r"\w+", query.lower(), flags=re.UNICODE)
        keywords: list[str] = []
        for word in words:
            if len(word) <= 2 or word in stop_words:
                continue
            if word not in keywords:
                keywords.append(word)
        return keywords

    def _normalize_query(self, query: str) -> str:
        normalized = " ".join(query.split())
        replacements = {
            "hiểu trưởng": "hiệu trưởng",
            "hỉệu trưởng": "hiệu trưởng",
            "hiệu trưỏng": "hiệu trưởng",
            "hiệu truong": "hiệu trưởng",
            "hieu truong": "hiệu trưởng",
        }
        folded = _fold_text(normalized)
        for typo, replacement in replacements.items():
            if _fold_text(typo) in folded:
                normalized = re.sub(typo, replacement, normalized, flags=re.IGNORECASE)
                folded = _fold_text(normalized)
        return normalized

    def _search_entities(self, fragment: str, limit: int = 10) -> List[Dict[str, Any]]:
        query = """
        MATCH (n)
        WHERE n.id IS NOT NULL
          AND (
            toLower(coalesce(n.name, '')) CONTAINS toLower($fragment)
            OR any(alias IN coalesce(n.aliases, []) WHERE toLower(toString(alias)) CONTAINS toLower($fragment))
            OR any(desc IN coalesce(n.description, []) WHERE toLower(toString(desc)) CONTAINS toLower($fragment))
          )
        WITH n,
          CASE
            WHEN toLower(coalesce(n.name, '')) = toLower($fragment) THEN 100
            WHEN any(alias IN coalesce(n.aliases, []) WHERE toLower(toString(alias)) = toLower($fragment)) THEN 95
            WHEN any(alias IN coalesce(n.aliases, []) WHERE toLower(toString(alias)) CONTAINS toLower($fragment)) THEN 90
            WHEN toLower(coalesce(n.name, '')) CONTAINS toLower($fragment) THEN 80
            WHEN any(desc IN coalesce(n.description, []) WHERE toLower(toString(desc)) CONTAINS toLower($fragment)) THEN 60
            ELSE 10
          END as score
        RETURN n.id as id, coalesce(n.name, n.id) as name, labels(n) as labels,
               properties(n) as properties, score as score
        ORDER BY score DESC, size(coalesce(n.name, n.id)) ASC
        LIMIT $limit
        """

        with self.driver.session() as session:
            return [record.data() for record in session.run(query, {"fragment": fragment, "limit": limit})]

    def _search_relationships(self, fragment: str, limit: int = 20) -> List[Dict[str, Any]]:
        query = """
        MATCH (s)-[r]->(t)
        WHERE s.id IS NOT NULL AND t.id IS NOT NULL
          AND (
            toLower(type(r)) CONTAINS toLower($fragment)
            OR any(desc IN coalesce(r.description, []) WHERE toLower(toString(desc)) CONTAINS toLower($fragment))
            OR toLower(coalesce(s.name, '')) CONTAINS toLower($fragment)
            OR toLower(coalesce(t.name, '')) CONTAINS toLower($fragment)
            OR any(alias IN coalesce(s.aliases, []) WHERE toLower(toString(alias)) CONTAINS toLower($fragment))
            OR any(alias IN coalesce(t.aliases, []) WHERE toLower(toString(alias)) CONTAINS toLower($fragment))
          )
        WITH s, r, t,
          CASE
            WHEN toLower(type(r)) = toLower($fragment) THEN 100
            WHEN any(desc IN coalesce(r.description, []) WHERE toLower(toString(desc)) CONTAINS toLower($fragment)) THEN 90
            WHEN any(alias IN coalesce(s.aliases, []) WHERE toLower(toString(alias)) CONTAINS toLower($fragment)) THEN 80
            WHEN any(alias IN coalesce(t.aliases, []) WHERE toLower(toString(alias)) CONTAINS toLower($fragment)) THEN 80
            WHEN toLower(coalesce(s.name, '')) CONTAINS toLower($fragment) THEN 70
            WHEN toLower(coalesce(t.name, '')) CONTAINS toLower($fragment) THEN 70
            WHEN toLower(type(r)) CONTAINS toLower($fragment) THEN 50
            ELSE 10
          END as score
        RETURN s.id as source_id, coalesce(s.name, s.id) as source, labels(s) as source_labels,
               properties(s) as source_props, type(r) as relation, properties(r) as rel_props,
               t.id as target_id, coalesce(t.name, t.id) as target, labels(t) as target_labels,
               properties(t) as target_props, score as score
        ORDER BY score DESC
        LIMIT $limit
        """

        with self.driver.session() as session:
            return [record.data() for record in session.run(query, {"fragment": fragment, "limit": limit})]

    def _get_entity_details(self, entity_id: str) -> Dict[str, Any] | None:
        query = """
        MATCH (n {id: $entity_id})
        RETURN n.id as id, coalesce(n.name, n.id) as name, labels(n) as labels,
               properties(n) as properties
        """

        with self.driver.session() as session:
            record = session.run(query, {"entity_id": entity_id}).single()
            return record.data() if record else None

    def _get_relationships(self, entity_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        query = """
        MATCH (n {id: $entity_id})-[r]-(m)
        WHERE m.id IS NOT NULL
        RETURN n.id as source_id, coalesce(n.name, n.id) as source, labels(n) as source_labels,
               properties(n) as source_props, type(r) as relation, properties(r) as rel_props,
               m.id as target_id, coalesce(m.name, m.id) as target, labels(m) as target_labels,
               properties(m) as target_props
        LIMIT $limit
        """

        with self.driver.session() as session:
            return [record.data() for record in session.run(query, {"entity_id": entity_id, "limit": limit})]

    def _details_from_rel(self, rel: dict[str, Any], side: str) -> dict[str, Any] | None:
        entity_id = rel.get(f"{side}_id")
        if not entity_id:
            return None
        return {
            "id": entity_id,
            "name": rel.get(side) or entity_id,
            "labels": rel.get(f"{side}_labels") or [],
            "properties": rel.get(f"{side}_props") or {},
            "score": rel.get("score") or rel.get("retrieval_score") or 0.0,
        }

    def _build_markdown_index(self) -> dict[str, Path]:
        if self._markdown_index is not None:
            return self._markdown_index
        index: dict[str, Path] = {}
        if self.raw_markdown_dir.exists():
            for path in self.raw_markdown_dir.rglob("*.md"):
                index[path.stem] = path
        self._markdown_index = index
        return index

    def _load_markdown_chunk(self, chunk_id: str) -> tuple[str | None, str | None]:
        index = self._build_markdown_index()
        doc_id = _doc_id_from_chunk_id(chunk_id)
        path = index.get(doc_id) or index.get(chunk_id)
        if path is None or not path.exists():
            return None, None

        text = path.read_text(encoding="utf-8", errors="ignore").strip()
        if len(text) > 1800:
            text = text[:1800].rsplit(" ", 1)[0].strip() + "..."
        return str(path), text
