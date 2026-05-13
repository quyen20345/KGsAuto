"""Neo4j adapter for the unified GraphSearch runtime."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import unicodedata
from typing import Any, Dict, Iterable, List

CONTEXT_PATTERN = (
    r"Knowledge Graph Data \(Entity\):\s*```json\s*(.*?)\s*```.*?"
    r"Knowledge Graph Data \(Relationship\):\s*```json\s*(.*?)\s*```.*?"
    r"Document Chunks.*?```json\s*(.*?)\s*```.*?"
    r"Reference Document List.*?```(?:json|text)?\s*(.*?)\s*```"
)
IDENTIFIER_SPLIT_RE = re.compile(r"[_\-/\\.]+")
PUNCTUATION_RE = re.compile(r"[^\w\s]", re.UNICODE)
WHITESPACE_RE = re.compile(r"\s+")
ACRONYM_RE = re.compile(r"\b[A-ZĐ]{2,}[A-Z0-9Đ]*\b")
STOPWORDS = {
    "toi", "tôi", "em", "hoi", "hỏi", "cho", "ve", "về", "thi", "thì", "la", "là", "duoc", "được",
    "ai", "gi", "gì", "nao", "nào", "nhung", "những", "cac", "các", "cua", "của", "co", "có",
}
LOGGER = logging.getLogger(__name__)


def normalize_vietnamese_text(value: Any) -> str:
    text = WHITESPACE_RE.sub(" ", str(value or "")).strip().lower()
    text = text.replace("đ", "d")
    decomposed = unicodedata.normalize("NFD", text)
    without_marks = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    without_identifiers = IDENTIFIER_SPLIT_RE.sub(" ", without_marks)
    without_punctuation = PUNCTUATION_RE.sub(" ", without_identifiers)
    return WHITESPACE_RE.sub(" ", without_punctuation).strip()


def split_identifier_variants(value: Any) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    split_text = WHITESPACE_RE.sub(" ", IDENTIFIER_SPLIT_RE.sub(" ", text)).strip()
    variants = [text]
    if split_text and split_text != text:
        variants.append(split_text)
    variants.extend(part for part in split_text.split() if len(part) >= 2)
    return _dedupe_text(variants)


def expand_keyword_variants(term: str) -> list[str]:
    variants = [term, normalize_vietnamese_text(term)]
    variants.extend(split_identifier_variants(term))
    normalized_variants = [normalize_vietnamese_text(variant) for variant in variants]
    return _dedupe_text([*variants, *normalized_variants])


def deterministic_query_terms(query: str, max_terms: int = 12) -> list[str]:
    candidates: list[str] = []
    candidates.extend(match.group(0) for match in ACRONYM_RE.finditer(query))
    candidates.extend(re.findall(r"['\"]([^'\"]+)['\"]", query))
    cleaned = PUNCTUATION_RE.sub(" ", query)
    words = [word for word in WHITESPACE_RE.split(cleaned.strip()) if word]
    for size in (4, 3, 2, 1):
        for index in range(0, max(0, len(words) - size + 1)):
            phrase = " ".join(words[index:index + size])
            normalized = normalize_vietnamese_text(phrase)
            if not normalized or normalized in STOPWORDS:
                continue
            if size == 1 and (len(normalized) < 3 or normalized in STOPWORDS):
                continue
            candidates.append(phrase)
    expanded: list[str] = []
    for candidate in candidates:
        expanded.extend(expand_keyword_variants(candidate))
    return _dedupe_text(expanded)[:max_terms]


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

    def __init__(self, top_k: int = 5, config: Any | None = None):
        from apps.graph_api.neo4j import get_driver
        from services.rag_system.config import RAGConfig

        self.driver = get_driver()
        self.config = config or RAGConfig()
        self.top_k = top_k
        self.keyword_max_terms = getattr(self.config, "graph_keyword_max_terms", 16)
        self.keyword_timeout_seconds = getattr(self.config, "graph_keyword_timeout_seconds", 15.0)
        self.fulltext_candidate_limit = getattr(self.config, "graph_fulltext_candidate_limit", 50)
        self.neighbor_limit_per_entity = getattr(self.config, "graph_neighbor_limit_per_entity", 10)
        self.fulltext_entity_index = getattr(self.config, "graph_fulltext_entity_index", "kg_entity_search")
        self.fulltext_relationship_index = getattr(self.config, "graph_fulltext_relationship_index", "kg_relationship_search")
        self.enable_relationship_fulltext = getattr(self.config, "graph_enable_relationship_fulltext", True)
        self.enable_substring_fallback = getattr(self.config, "graph_enable_substring_fallback", True)
        self.substring_fallback_limit = getattr(self.config, "graph_substring_fallback_limit", 20)
        self.description_fallback_min_term_length = getattr(self.config, "graph_description_fallback_min_term_length", 5)
        self.allow_legacy_scan_fallback = getattr(self.config, "graph_allow_legacy_scan_fallback", True)
        self._available_indexes: set[str] | None = None
        self._store = None

    async def aquery_context(self, question: str) -> str:
        started_at = time.perf_counter()
        keywords = await self._extract_keywords_async(question)
        entities_by_id: dict[str, dict[str, Any]] = {}
        relationships_by_key: dict[str, dict[str, Any]] = {}
        chunks_by_id: dict[str, dict[str, Any]] = {}
        sources_by_id: dict[str, dict[str, Any]] = {}

        def add_vector_chunk(chunk: dict[str, Any]) -> None:
            chunk_id = str(chunk.get("chunk_id") or "").strip()
            content = str(chunk.get("text") or "").strip()
            if not chunk_id or not content or chunk_id in chunks_by_id:
                return
            source = chunk_id
            reference_id = len(sources_by_id)
            chunks_by_id[chunk_id] = {
                "chunk_id": chunk_id,
                "section": chunk.get("section"),
                "content": content,
                "reference_id": reference_id,
                "score": chunk.get("score"),
            }
            sources_by_id[chunk_id] = {
                "reference_id": reference_id,
                "source": source,
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
        graph_started_at = time.perf_counter()
        entity_task = asyncio.to_thread(self._search_entities_batch, keywords, self.top_k * 4)
        vector_task = asyncio.to_thread(self._search_chunks, question)
        entity_hits, vector_chunks = await asyncio.gather(entity_task, vector_task)

        for entity in entity_hits:
            add_entity_from_details(entity)

        relationship_tasks = [
            asyncio.to_thread(
                self._get_relationships_batch,
                list(entities_by_id),
                self.neighbor_limit_per_entity,
            )
        ]
        if self.enable_relationship_fulltext:
            relationship_tasks.append(asyncio.to_thread(self._search_relationships_batch, keywords, self.top_k * 3))

        relationship_results = await asyncio.gather(*relationship_tasks)
        for rels in relationship_results:
            for rel in rels:
                add_relationship(rel)
                add_entity_from_details(self._details_from_rel(rel, "source"))
                add_entity_from_details(self._details_from_rel(rel, "target"))

        for chunk in vector_chunks:
            add_vector_chunk(chunk)

        LOGGER.info(
            "graph_search_context timings total_ms=%.1f graph_ms=%.1f keywords=%d entities=%d relationships=%d",
            (time.perf_counter() - started_at) * 1000,
            (time.perf_counter() - graph_started_at) * 1000,
            len(keywords),
            len(entities_by_id),
            len(relationships_by_key),
        )

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

    async def aquery_answer(self, question: str, context: str | None = None) -> str:
        from services.rag_system.graph.graph_search.utils import openai_complete

        if context is None:
            context = await self.aquery_context(question)
        prompt = f"""Based only on the following knowledge graph and document evidence, answer the question in Vietnamese.

Question: {question}

Evidence:
{context}

If the evidence is insufficient, say that the provided graph/document evidence is not enough."""

        return await openai_complete(prompt=prompt)

    def _get_store(self):
        if self._store is None:
            from services.rag_system.retrieval.store import Store

            self._store = Store(self.config)
        return self._store

    def _search_chunks(self, question: str) -> list[dict[str, Any]]:
        store = self._get_store()
        if not store.collection_exists():
            return []
        return store.search(question, top_k=self.top_k)

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
        deterministic = deterministic_query_terms(query, max_terms=self.keyword_max_terms)
        try:
            llm_keywords = await self._extract_llm_keywords(query)
        except RuntimeError as exc:
            LOGGER.warning("Graph keyword extraction failed; using deterministic terms: %s", exc)
            llm_keywords = {}
        candidates = [
            *llm_keywords.get("must_keep_phrases", []),
            *deterministic,
            *llm_keywords.get("low_level_keywords", []),
            *llm_keywords.get("expanded_keywords", []),
            *llm_keywords.get("high_level_keywords", []),
        ]
        expanded: list[str] = []
        for candidate in candidates:
            expanded.extend(expand_keyword_variants(candidate))
        keywords = _dedupe_text(expanded)[: self.keyword_max_terms]
        if not keywords:
            query_preview = " ".join(query.split())[:160]
            raise RuntimeError(f"Graph keyword extraction returned no keywords for query: {query_preview}")
        return keywords

    async def _extract_llm_keywords(self, query: str) -> dict[str, list[str]]:
        from services.rag_system.graph.graph_search.components import GraphKeywordExtractionError, keywords_extraction

        try:
            return await asyncio.wait_for(keywords_extraction(query), timeout=self.keyword_timeout_seconds)
        except asyncio.TimeoutError as exc:
            query_preview = " ".join(query.split())[:160]
            raise RuntimeError(
                f"Graph keyword extraction timed out after {self.keyword_timeout_seconds:.1f}s for query: {query_preview}"
            ) from exc
        except GraphKeywordExtractionError as exc:
            query_preview = " ".join(query.split())[:160]
            raise RuntimeError(f"Graph keyword extraction failed for query: {query_preview}: {exc}") from exc

    def _has_index(self, index_name: str) -> bool:
        if self._available_indexes is None:
            try:
                with self.driver.session() as session:
                    self._available_indexes = {
                        record["name"] for record in session.run("SHOW INDEXES YIELD name RETURN name")
                    }
            except Exception as exc:
                LOGGER.warning("Unable to inspect Neo4j indexes: %s", exc)
                self._available_indexes = set()
        return index_name in self._available_indexes

    def _escape_lucene(self, term: str) -> str:
        return re.sub(r'([+\-&|!(){}\[\]^"~*?:\\/])', r"\\\1", term)

    def _build_lucene_query(self, terms: list[str]) -> str:
        clauses: list[str] = []
        for term in terms:
            normalized = normalize_vietnamese_text(term)
            if not normalized:
                continue
            escaped = self._escape_lucene(normalized)
            if " " in normalized:
                clauses.append(f'"{escaped}"')
            else:
                clauses.append(escaped)
                if 3 <= len(normalized) <= 12:
                    clauses.append(f"{escaped}*")
        return " OR ".join(_dedupe_text(clauses)) or "__no_match__"

    def _score_entity(self, entity: dict[str, Any], terms: list[str], fulltext_score: float = 0.0) -> float:
        properties = entity.get("properties", {}) or {}
        names = [entity.get("name"), properties.get("name")]
        aliases = _as_list(properties.get("aliases")) + _as_list(properties.get("search_aliases"))
        descriptions = _as_list(properties.get("description")) + _as_list(properties.get("search_description"))
        search_text = str(properties.get("search_text") or "")
        normalized_terms = [normalize_vietnamese_text(term) for term in terms if normalize_vietnamese_text(term)]
        normalized_names = [normalize_vietnamese_text(name) for name in names if normalize_vietnamese_text(name)]
        normalized_aliases = [normalize_vietnamese_text(alias) for alias in aliases if normalize_vietnamese_text(alias)]
        normalized_descriptions = [normalize_vietnamese_text(desc) for desc in descriptions if normalize_vietnamese_text(desc)]

        score = float(fulltext_score or entity.get("score") or entity.get("fulltext_score") or 0.0)
        for term in normalized_terms:
            if term in normalized_names:
                score = max(score, 100.0)
            if term in normalized_aliases:
                score = max(score, 95.0)
            if any(term in alias for alias in normalized_aliases):
                score = max(score, 90.0)
            if any(term in name for name in normalized_names):
                score = max(score, 80.0)
            if term in search_text:
                score = max(score, 70.0)
            if len(term) >= self.description_fallback_min_term_length and any(term in desc for desc in normalized_descriptions):
                score = max(score, 60.0)
        return score

    def _search_entities_batch(self, terms: list[str], limit: int = 20) -> List[Dict[str, Any]]:
        results: list[dict[str, Any]] = []
        if self._has_index(self.fulltext_entity_index):
            query = """
            CALL db.index.fulltext.queryNodes($index_name, $query, {limit: $candidate_limit})
            YIELD node, score
            WHERE node.id IS NOT NULL
            RETURN node.id as id, coalesce(node.name, node.id) as name, labels(node) as labels,
                   properties(node) as properties, score as fulltext_score
            ORDER BY fulltext_score DESC
            LIMIT $limit
            """
            with self.driver.session() as session:
                results = [
                    record.data()
                    for record in session.run(
                        query,
                        {
                            "index_name": self.fulltext_entity_index,
                            "query": self._build_lucene_query(terms),
                            "candidate_limit": self.fulltext_candidate_limit,
                            "limit": limit,
                        },
                    )
                ]
        elif not self.allow_legacy_scan_fallback:
            LOGGER.warning("Neo4j full-text index %s is unavailable", self.fulltext_entity_index)
        else:
            LOGGER.warning("Neo4j full-text index %s is unavailable; using batched substring fallback", self.fulltext_entity_index)

        if self.enable_substring_fallback and (len(results) < min(limit, self.top_k)):
            exclude_ids = [str(result.get("id")) for result in results if result.get("id")]
            results.extend(self._search_entities_substring_fallback(terms, exclude_ids, self.substring_fallback_limit))

        by_id: dict[str, dict[str, Any]] = {}
        for result in results:
            entity_id = str(result.get("id") or "")
            if not entity_id:
                continue
            score = self._score_entity(result, terms, float(result.get("fulltext_score") or 0.0))
            result["score"] = score
            if entity_id not in by_id or score > float(by_id[entity_id].get("score") or 0.0):
                by_id[entity_id] = result
        return sorted(by_id.values(), key=lambda item: item.get("score", 0.0), reverse=True)[:limit]

    def _search_entities_substring_fallback(
        self, terms: list[str], exclude_ids: list[str] | None = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        query = """
        UNWIND $terms AS term
        MATCH (n)
        WHERE n.id IS NOT NULL
          AND NOT n.id IN $exclude_ids
          AND (
            toLower(coalesce(n.name, '')) CONTAINS toLower(term)
            OR any(alias IN coalesce(n.aliases, []) WHERE toLower(toString(alias)) CONTAINS toLower(term))
            OR coalesce(n.search_text, '') CONTAINS term
            OR (
              size(term) >= $description_min_term_length
              AND any(desc IN coalesce(n.description, []) WHERE toLower(toString(desc)) CONTAINS toLower(term))
            )
          )
        RETURN DISTINCT n.id as id, coalesce(n.name, n.id) as name, labels(n) as labels,
               properties(n) as properties, 0.0 as fulltext_score
        LIMIT $limit
        """
        normalized_terms = _dedupe_text([normalize_vietnamese_text(term) for term in terms if normalize_vietnamese_text(term)])
        with self.driver.session() as session:
            return [
                record.data()
                for record in session.run(
                    query,
                    {
                        "terms": normalized_terms,
                        "exclude_ids": exclude_ids or [],
                        "description_min_term_length": self.description_fallback_min_term_length,
                        "limit": limit,
                    },
                )
            ]

    async def _asearch_entities(self, fragment: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Async wrapper for _search_entities using thread pool."""
        import asyncio
        return await asyncio.to_thread(self._search_entities, fragment, limit)

    async def _asearch_relationships(self, fragment: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Async wrapper for _search_relationships using thread pool."""
        import asyncio
        return await asyncio.to_thread(self._search_relationships, fragment, limit)

    async def _aget_entity_details(self, entity_id: str) -> Dict[str, Any] | None:
        """Async wrapper for _get_entity_details using thread pool."""
        import asyncio
        return await asyncio.to_thread(self._get_entity_details, entity_id)

    async def _aget_relationships(self, entity_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Async wrapper for _get_relationships using thread pool."""
        import asyncio
        return await asyncio.to_thread(self._get_relationships, entity_id, limit)

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

    def _get_relationships_batch(self, entity_ids: list[str], limit_per_entity: int = 10) -> List[Dict[str, Any]]:
        if not entity_ids:
            return []
        query = """
        UNWIND $entity_ids AS entity_id
        MATCH (n {id: entity_id})-[r]-(m)
        WHERE m.id IS NOT NULL
        WITH entity_id, n, r, m
        ORDER BY coalesce(r.weight, 1.0) DESC
        WITH entity_id, collect({n:n, r:r, m:m})[..$limit_per_entity] AS rels
        UNWIND rels AS item
        RETURN item.n.id as source_id, coalesce(item.n.name, item.n.id) as source,
               labels(item.n) as source_labels, properties(item.n) as source_props,
               type(item.r) as relation, properties(item.r) as rel_props,
               item.m.id as target_id, coalesce(item.m.name, item.m.id) as target,
               labels(item.m) as target_labels, properties(item.m) as target_props,
               0.0 as score
        """
        with self.driver.session() as session:
            return [
                record.data()
                for record in session.run(
                    query,
                    {"entity_ids": entity_ids, "limit_per_entity": limit_per_entity},
                )
            ]

    def _search_relationships_batch(self, terms: list[str], limit: int = 20) -> List[Dict[str, Any]]:
        if not self._has_index(self.fulltext_relationship_index):
            return []
        query = """
        CALL db.index.fulltext.queryRelationships($index_name, $query, {limit: $limit})
        YIELD relationship, score
        MATCH (s)-[relationship]->(t)
        WHERE s.id IS NOT NULL AND t.id IS NOT NULL
        RETURN s.id as source_id, coalesce(s.name, s.id) as source, labels(s) as source_labels,
               properties(s) as source_props, type(relationship) as relation, properties(relationship) as rel_props,
               t.id as target_id, coalesce(t.name, t.id) as target, labels(t) as target_labels,
               properties(t) as target_props, score as score
        ORDER BY score DESC
        LIMIT $limit
        """
        with self.driver.session() as session:
            return [
                record.data()
                for record in session.run(
                    query,
                    {
                        "index_name": self.fulltext_relationship_index,
                        "query": self._build_lucene_query(terms),
                        "limit": limit,
                    },
                )
            ]

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
