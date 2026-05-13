"""Shared infrastructure configuration for KGsAuto services.

This is the single source of truth for environment-based configuration.
Every backend service imports constants from here instead of reading os.getenv
directly.  The .env file (git-ignored) provides local overrides; .env.example
documents all supported variables.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv


load_dotenv()


# ── Neo4j ────────────────────────────────────────────────────────────────
NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "12345678")

# ── Qdrant ───────────────────────────────────────────────────────────────
QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")

# ── LLM provider defaults ────────────────────────────────────────────────
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "OpenAICompatible")
LLM_MODEL: str = os.getenv("LLM_MODEL", "cx/gpt-5.3-codex")

# ── OpenAI-compatible provider ───────────────────────────────────────────
OPENAI_COMPATIBLE_API_KEY: str | None = os.getenv("OPENAI_COMPATIBLE_API_KEY")
OPENAI_COMPATIBLE_BASE_URL: str | None = os.getenv("OPENAI_COMPATIBLE_BASE_URL")
OPENAI_COMPATIBLE_MODEL: str | None = os.getenv("OPENAI_COMPATIBLE_MODEL")

# ── Gemini provider ──────────────────────────────────────────────────────
GOOGLE_API_KEY: str | None = os.getenv("GOOGLE_API_KEY")
DEFAULT_MODEL: str | None = os.getenv("DEFAULT_MODEL", "gemini-2.5-flash")

# ── Embedding ────────────────────────────────────────────────────────────
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-mpnet-base-v2")
EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "768"))
EMBEDDING_DEVICE: str = os.getenv("EMBEDDING_DEVICE", "cpu")

# ── RAG data & collections ───────────────────────────────────────────────
RAG_MARKDOWN_DIR: str = os.getenv("RAG_MARKDOWN_DIR", "data/raw/uet")
RAG_OUTPUT_DIR: str = os.getenv("RAG_OUTPUT_DIR", "data/rag_system")
RAG_MARKDOWN_COLLECTION: str = os.getenv("RAG_MARKDOWN_COLLECTION", "rag_markdown_chunks")
RAG_ENTITY_COLLECTION: str = os.getenv("RAG_ENTITY_COLLECTION", "rag_entities")

# ── RAG chunking ─────────────────────────────────────────────────────────
RAG_CHUNK_STRATEGY: str = os.getenv("RAG_CHUNK_STRATEGY", "section")
RAG_CHUNK_MAX_TOKENS: int = int(os.getenv("RAG_CHUNK_MAX_TOKENS", "100"))
RAG_CHUNK_OVERLAP_TOKENS: int = int(os.getenv("RAG_CHUNK_OVERLAP_TOKENS", "20"))
RAG_CHUNK_MIN_TOKENS: int = int(os.getenv("RAG_CHUNK_MIN_TOKENS", "15"))

# ── GraphSearch tuning ───────────────────────────────────────────────────
GRAPH_KEYWORD_MAX_TERMS: int = int(os.getenv("GRAPH_KEYWORD_MAX_TERMS", "16"))
GRAPH_KEYWORD_TIMEOUT_SECONDS: float = float(
    os.getenv("GRAPH_KEYWORD_TIMEOUT_SECONDS", "60.0")
)
GRAPH_FULLTEXT_CANDIDATE_LIMIT: int = int(os.getenv("GRAPH_FULLTEXT_CANDIDATE_LIMIT", "50"))
GRAPH_NEIGHBOR_LIMIT_PER_ENTITY: int = int(os.getenv("GRAPH_NEIGHBOR_LIMIT_PER_ENTITY", "10"))
GRAPH_FULLTEXT_ENTITY_INDEX: str = os.getenv("GRAPH_FULLTEXT_ENTITY_INDEX", "kg_entity_search")
GRAPH_FULLTEXT_RELATIONSHIP_INDEX: str = os.getenv("GRAPH_FULLTEXT_RELATIONSHIP_INDEX", "kg_relationship_search")
GRAPH_ENABLE_RELATIONSHIP_FULLTEXT: bool = os.getenv("GRAPH_ENABLE_RELATIONSHIP_FULLTEXT", "true").lower() == "true"
GRAPH_ENABLE_SUBSTRING_FALLBACK: bool = os.getenv("GRAPH_ENABLE_SUBSTRING_FALLBACK", "true").lower() == "true"
GRAPH_SUBSTRING_FALLBACK_LIMIT: int = int(os.getenv("GRAPH_SUBSTRING_FALLBACK_LIMIT", "20"))
GRAPH_DESCRIPTION_FALLBACK_MIN_TERM_LENGTH: int = int(os.getenv("GRAPH_DESCRIPTION_FALLBACK_MIN_TERM_LENGTH", "5"))
GRAPH_ALLOW_LEGACY_SCAN_FALLBACK: bool = os.getenv("GRAPH_ALLOW_LEGACY_SCAN_FALLBACK", "true").lower() == "true"
GRAPHSEARCH_MAX_SUB_QUERIES: int = int(os.getenv("GRAPHSEARCH_MAX_SUB_QUERIES", "5"))
GRAPHSEARCH_MAX_EXPANDED_QUERIES: int = int(
    os.getenv("GRAPHSEARCH_MAX_EXPANDED_QUERIES", "3")
)

# ── Evaluation ───────────────────────────────────────────────────────────
RAGAS_SCORE_MAX_WORKERS: int = int(os.getenv("RAGAS_SCORE_MAX_WORKERS", "2"))
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL: str | None = os.getenv("OPENAI_BASE_URL")
OPENAI_MODEL: str | None = os.getenv("OPENAI_MODEL")
CX_API_KEY: str | None = os.getenv("CX_API_KEY")
