"""Shared infrastructure configuration for KGsAuto services.

This module is the compatibility facade for environment-based configuration.
Backend services should read settings or constants from here instead of reading
process environment variables directly.
"""

from __future__ import annotations

import os
import warnings
from dataclasses import dataclass
from typing import Callable, TypeVar

from dotenv import load_dotenv


T = TypeVar("T")

if os.getenv("KGSAUTO_LOAD_DOTENV", "true").lower() not in {"0", "false", "no", "off"}:
    load_dotenv()


class ConfigValidationError(RuntimeError):
    """Raised when a runtime profile is missing required configuration."""


@dataclass(frozen=True)
class EnvValue:
    value: str | None
    source: str | None = None
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class Neo4jSettings:
    uri: str
    user: str
    password: str


@dataclass(frozen=True)
class QdrantSettings:
    url: str


@dataclass(frozen=True)
class LLMSettings:
    provider: str
    model: str
    openai_compatible_api_key: str | None
    openai_compatible_api_key_source: str | None
    openai_compatible_base_url: str | None
    openai_compatible_model: str | None
    google_api_key: str | None
    default_model: str | None
    openai_api_key: str | None
    openai_base_url: str | None
    openai_model: str | None
    cx_api_key: str | None


@dataclass(frozen=True)
class EmbeddingSettings:
    model: str
    dim: int
    device: str


@dataclass(frozen=True)
class RAGSettings:
    markdown_dir: str
    output_dir: str
    markdown_collection: str
    entity_collection: str
    chunk_strategy: str
    chunk_max_tokens: int
    chunk_overlap_tokens: int
    chunk_min_tokens: int


@dataclass(frozen=True)
class GraphSettings:
    keyword_max_terms: int
    keyword_timeout_seconds: float
    fulltext_candidate_limit: int
    neighbor_limit_per_entity: int
    fulltext_entity_index: str
    fulltext_relationship_index: str
    enable_relationship_fulltext: bool
    enable_substring_fallback: bool
    substring_fallback_limit: int
    description_fallback_min_term_length: int
    allow_legacy_scan_fallback: bool
    graphsearch_max_sub_queries: int
    graphsearch_max_expanded_queries: int
    entity_search_top_k_multiplier: int
    relationship_search_top_k_multiplier: int
    context_entity_top_k_multiplier: int
    context_relationship_top_k_multiplier: int
    context_description_max_chars: int
    score_exact_name: float
    score_exact_alias: float
    score_partial_alias: float
    score_partial_name: float
    score_search_text: float
    score_description: float


@dataclass(frozen=True)
class EvaluationSettings:
    ragas_score_max_workers: int
    openai_api_key: str | None
    openai_base_url: str | None
    openai_model: str | None
    ragas_llm_api_key: str | None
    ragas_llm_base_url: str | None
    ragas_llm_model: str | None
    ragas_embedding_api_key: str | None
    ragas_embedding_model: str
    ragas_embedding_base_url: str
    ragas_embedding_delay_seconds: float
    ragas_score_max_retries: int
    ragas_score_max_wait_seconds: int
    ragas_score_timeout_seconds: int
    ragas_llm_temperature: float
    qdrant_upsert_batch_size: int


@dataclass(frozen=True)
class AppSettings:
    strict: bool
    neo4j: Neo4jSettings
    qdrant: QdrantSettings
    llm: LLMSettings
    embedding: EmbeddingSettings
    rag: RAGSettings
    graph: GraphSettings
    evaluation: EvaluationSettings

    @classmethod
    def from_env(cls) -> "AppSettings":
        openai_compatible_key = _env_alias(
            "OPENAI_COMPATIBLE_API_KEY",
            aliases=("OPENAI_API_KEY", "CX_API_KEY"),
        )
        ragas_llm_api_key = _env_alias(
            "OPENAI_API_KEY",
            aliases=("OPENAI_COMPATIBLE_API_KEY", "CX_API_KEY"),
        )
        ragas_llm_base_url = _env_alias("OPENAI_BASE_URL", aliases=("OPENAI_COMPATIBLE_BASE_URL",))
        ragas_llm_model = _env_alias("OPENAI_MODEL", aliases=("OPENAI_COMPATIBLE_MODEL",))
        ragas_embedding_key = _env_alias("RAGAS_EMBEDDING_API_KEY", aliases=("NVIDIA_API_KEY",))
        ragas_embedding_model = _env_alias(
            "RAGAS_EMBEDDING_MODEL",
            aliases=("NVIDIA_EMBED_MODEL",),
            default="nvidia/llama-3.2-nemoretriever-300m-embed-v1",
        )
        ragas_embedding_base_url = _env_alias(
            "RAGAS_EMBEDDING_BASE_URL",
            aliases=("NVIDIA_BASE_URL",),
            default="https://integrate.api.nvidia.com/v1",
        )

        return cls(
            strict=_env_bool("CONFIG_STRICT", False),
            neo4j=Neo4jSettings(
                uri=_env_str("NEO4J_URI", "bolt://localhost:7687"),
                user=_env_str("NEO4J_USER", "neo4j"),
                password=_env_str("NEO4J_PASSWORD", "12345678"),
            ),
            qdrant=QdrantSettings(url=_env_str("QDRANT_URL", "http://localhost:6333")),
            llm=LLMSettings(
                provider=_env_str("LLM_PROVIDER", "OpenAICompatible"),
                model=_env_str("LLM_MODEL", "cx/gpt-5.3-codex"),
                openai_compatible_api_key=openai_compatible_key.value,
                openai_compatible_api_key_source=openai_compatible_key.source,
                openai_compatible_base_url=_env_optional("OPENAI_COMPATIBLE_BASE_URL"),
                openai_compatible_model=_env_optional("OPENAI_COMPATIBLE_MODEL"),
                google_api_key=_env_optional("GOOGLE_API_KEY"),
                default_model=_env_str("DEFAULT_MODEL", "gemini-2.5-flash"),
                openai_api_key=_env_optional("OPENAI_API_KEY"),
                openai_base_url=_env_optional("OPENAI_BASE_URL"),
                openai_model=_env_optional("OPENAI_MODEL"),
                cx_api_key=_env_optional("CX_API_KEY"),
            ),
            embedding=EmbeddingSettings(
                model=_env_str("EMBEDDING_MODEL", "paraphrase-multilingual-mpnet-base-v2"),
                dim=_env_int("EMBEDDING_DIM", 768),
                device=_env_str("EMBEDDING_DEVICE", "cpu"),
            ),
            rag=RAGSettings(
                markdown_dir=_env_str("RAG_MARKDOWN_DIR", "data/raw/uet"),
                output_dir=_env_str("RAG_OUTPUT_DIR", "data/rag_system"),
                markdown_collection=_env_str("RAG_MARKDOWN_COLLECTION", "rag_markdown_chunks"),
                entity_collection=_env_str("RAG_ENTITY_COLLECTION", "rag_entities"),
                chunk_strategy=_env_str("RAG_CHUNK_STRATEGY", "section"),
                chunk_max_tokens=_env_int("RAG_CHUNK_MAX_TOKENS", 100),
                chunk_overlap_tokens=_env_int("RAG_CHUNK_OVERLAP_TOKENS", 20),
                chunk_min_tokens=_env_int("RAG_CHUNK_MIN_TOKENS", 15),
            ),
            graph=GraphSettings(
                keyword_max_terms=_env_int("GRAPH_KEYWORD_MAX_TERMS", 16),
                keyword_timeout_seconds=_env_float("GRAPH_KEYWORD_TIMEOUT_SECONDS", 60.0),
                fulltext_candidate_limit=_env_int("GRAPH_FULLTEXT_CANDIDATE_LIMIT", 50),
                neighbor_limit_per_entity=_env_int("GRAPH_NEIGHBOR_LIMIT_PER_ENTITY", 10),
                fulltext_entity_index=_env_str("GRAPH_FULLTEXT_ENTITY_INDEX", "kg_entity_search"),
                fulltext_relationship_index=_env_str("GRAPH_FULLTEXT_RELATIONSHIP_INDEX", "kg_relationship_search"),
                enable_relationship_fulltext=_env_bool("GRAPH_ENABLE_RELATIONSHIP_FULLTEXT", True),
                enable_substring_fallback=_env_bool("GRAPH_ENABLE_SUBSTRING_FALLBACK", True),
                substring_fallback_limit=_env_int("GRAPH_SUBSTRING_FALLBACK_LIMIT", 20),
                description_fallback_min_term_length=_env_int("GRAPH_DESCRIPTION_FALLBACK_MIN_TERM_LENGTH", 5),
                allow_legacy_scan_fallback=_env_bool("GRAPH_ALLOW_LEGACY_SCAN_FALLBACK", True),
                graphsearch_max_sub_queries=_env_int("GRAPHSEARCH_MAX_SUB_QUERIES", 3),
                graphsearch_max_expanded_queries=_env_int("GRAPHSEARCH_MAX_EXPANDED_QUERIES", 1),
                entity_search_top_k_multiplier=_env_int("GRAPH_ENTITY_SEARCH_TOP_K_MULTIPLIER", 4),
                relationship_search_top_k_multiplier=_env_int("GRAPH_RELATIONSHIP_SEARCH_TOP_K_MULTIPLIER", 3),
                context_entity_top_k_multiplier=_env_int("GRAPH_CONTEXT_ENTITY_TOP_K_MULTIPLIER", 2),
                context_relationship_top_k_multiplier=_env_int("GRAPH_CONTEXT_RELATIONSHIP_TOP_K_MULTIPLIER", 3),
                context_description_max_chars=_env_int("GRAPH_CONTEXT_DESCRIPTION_MAX_CHARS", 1200),
                score_exact_name=_env_float("GRAPH_SCORE_EXACT_NAME", 100.0),
                score_exact_alias=_env_float("GRAPH_SCORE_EXACT_ALIAS", 95.0),
                score_partial_alias=_env_float("GRAPH_SCORE_PARTIAL_ALIAS", 90.0),
                score_partial_name=_env_float("GRAPH_SCORE_PARTIAL_NAME", 80.0),
                score_search_text=_env_float("GRAPH_SCORE_SEARCH_TEXT", 70.0),
                score_description=_env_float("GRAPH_SCORE_DESCRIPTION", 60.0),
            ),
            evaluation=EvaluationSettings(
                ragas_score_max_workers=_env_int("RAGAS_SCORE_MAX_WORKERS", 2),
                openai_api_key=_env_optional("OPENAI_API_KEY"),
                openai_base_url=_env_optional("OPENAI_BASE_URL"),
                openai_model=_env_optional("OPENAI_MODEL"),
                ragas_llm_api_key=ragas_llm_api_key.value,
                ragas_llm_base_url=ragas_llm_base_url.value,
                ragas_llm_model=ragas_llm_model.value,
                ragas_embedding_api_key=ragas_embedding_key.value,
                ragas_embedding_model=ragas_embedding_model.value or "nvidia/llama-3.2-nemoretriever-300m-embed-v1",
                ragas_embedding_base_url=ragas_embedding_base_url.value or "https://integrate.api.nvidia.com/v1",
                ragas_embedding_delay_seconds=_env_float("RAGAS_EMBEDDING_DELAY_SECONDS", 0.1),
                ragas_score_max_retries=_env_int("RAGAS_SCORE_MAX_RETRIES", 10),
                ragas_score_max_wait_seconds=_env_int("RAGAS_SCORE_MAX_WAIT_SECONDS", 120),
                ragas_score_timeout_seconds=_env_int("RAGAS_SCORE_TIMEOUT_SECONDS", 300),
                ragas_llm_temperature=_env_float("RAGAS_LLM_TEMPERATURE", 0.0),
                qdrant_upsert_batch_size=_env_int("QDRANT_UPSERT_BATCH_SIZE", 1000),
            ),
        )


def _env_optional(name: str) -> str | None:
    value = os.getenv(name)
    return value if value else None


def _env_str(name: str, default: str) -> str:
    return _env_optional(name) or default


def _env_int(name: str, default: int) -> int:
    return _parse_env(name, default, int)


def _env_float(name: str, default: float) -> float:
    return _parse_env(name, default, float)


def _env_bool(name: str, default: bool) -> bool:
    value = _env_optional(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigValidationError(f"Invalid boolean value for {name}: {value!r}")


def _parse_env(name: str, default: T, parser: Callable[[str], T]) -> T:
    value = _env_optional(name)
    if value is None:
        return default
    try:
        return parser(value)
    except ValueError as exc:
        raise ConfigValidationError(f"Invalid value for {name}: {value!r}") from exc


def _env_alias(canonical: str, aliases: tuple[str, ...] = (), default: str | None = None) -> EnvValue:
    canonical_value = _env_optional(canonical)
    alias_values = [(alias, value) for alias in aliases if (value := _env_optional(alias))]

    if canonical_value:
        _warn_conflicting_aliases(canonical, canonical_value, alias_values)
        return EnvValue(canonical_value, canonical, aliases)
    if alias_values:
        source, value = alias_values[0]
        _warn_deprecated_alias(canonical, source)
        _warn_conflicting_aliases(source, value, alias_values[1:])
        return EnvValue(value, source, aliases)
    return EnvValue(default, None, aliases)


def _warn_deprecated_alias(canonical: str, alias: str) -> None:
    warnings.warn(
        f"{alias} is being used as a legacy alias for {canonical}. Prefer {canonical}.",
        DeprecationWarning,
        stacklevel=3,
    )


def _warn_conflicting_aliases(canonical: str, canonical_value: str, alias_values: list[tuple[str, str]]) -> None:
    conflicts = [name for name, value in alias_values if value != canonical_value]
    if not conflicts:
        return
    message = f"Conflicting config values for {canonical} and aliases: {', '.join(conflicts)}. Using {canonical}."
    if _env_bool("CONFIG_STRICT", False):
        raise ConfigValidationError(message)
    warnings.warn(message, RuntimeWarning, stacklevel=3)


def validate_settings(profile: str = "base") -> None:
    validators = {
        "base": _validate_base,
        "graph_api": _validate_graph_api,
        "pipeline_api": _validate_pipeline_api,
        "rag": _validate_rag,
        "extraction": _validate_extraction,
        "evaluation": _validate_evaluation,
    }
    try:
        validator = validators[profile]
    except KeyError as exc:
        raise ConfigValidationError(f"Unknown config validation profile: {profile}") from exc
    validator()


def _validate_base() -> None:
    return None


def _validate_graph_api() -> None:
    _require(profile="graph_api", value=settings.neo4j.uri, canonical="NEO4J_URI")
    _require(profile="graph_api", value=settings.neo4j.user, canonical="NEO4J_USER")
    _require(profile="graph_api", value=settings.neo4j.password, canonical="NEO4J_PASSWORD")


def _validate_pipeline_api() -> None:
    _validate_graph_api()
    _require(profile="pipeline_api", value=settings.qdrant.url, canonical="QDRANT_URL")
    _require(profile="pipeline_api", value=settings.embedding.model, canonical="EMBEDDING_MODEL")


def _validate_rag() -> None:
    _require(profile="rag", value=settings.qdrant.url, canonical="QDRANT_URL")
    _validate_llm_provider("rag")


def _validate_extraction() -> None:
    _validate_llm_provider("extraction")


def _validate_evaluation() -> None:
    _require(
        profile="evaluation",
        value=settings.evaluation.ragas_llm_api_key,
        canonical="OPENAI_API_KEY",
        aliases=("OPENAI_COMPATIBLE_API_KEY", "CX_API_KEY"),
    )
    _require(
        profile="evaluation",
        value=settings.evaluation.ragas_llm_base_url,
        canonical="OPENAI_BASE_URL",
        aliases=("OPENAI_COMPATIBLE_BASE_URL",),
    )
    _require(
        profile="evaluation",
        value=settings.evaluation.ragas_llm_model,
        canonical="OPENAI_MODEL",
        aliases=("OPENAI_COMPATIBLE_MODEL",),
    )


def _validate_llm_provider(profile: str) -> None:
    provider = settings.llm.provider.lower()
    if provider in {"openai-compatible", "openaicompatible"}:
        _require(
            profile=profile,
            value=settings.llm.openai_compatible_api_key,
            canonical="OPENAI_COMPATIBLE_API_KEY",
            aliases=("OPENAI_API_KEY", "CX_API_KEY"),
        )
        _require(profile=profile, value=settings.llm.openai_compatible_base_url, canonical="OPENAI_COMPATIBLE_BASE_URL")
    elif provider == "gemini":
        _require(profile=profile, value=settings.llm.google_api_key, canonical="GOOGLE_API_KEY")
    elif provider == "openai":
        _require(profile=profile, value=settings.llm.openai_api_key, canonical="OPENAI_API_KEY")


def _require(profile: str, value: str | None, canonical: str, aliases: tuple[str, ...] = ()) -> None:
    if value:
        return
    alias_text = f" Accepted legacy aliases: {', '.join(aliases)}." if aliases else ""
    raise ConfigValidationError(
        f"Missing required config for profile '{profile}': {canonical}.{alias_text} "
        f"Set {canonical} in the backend .env file."
    )


settings = AppSettings.from_env()


# ── Backward-compatible constant exports ────────────────────────────────────
NEO4J_URI: str = settings.neo4j.uri
NEO4J_USER: str = settings.neo4j.user
NEO4J_PASSWORD: str = settings.neo4j.password

QDRANT_URL: str = settings.qdrant.url

LLM_PROVIDER: str = settings.llm.provider
LLM_MODEL: str = settings.llm.model

OPENAI_COMPATIBLE_API_KEY: str | None = settings.llm.openai_compatible_api_key
OPENAI_COMPATIBLE_BASE_URL: str | None = settings.llm.openai_compatible_base_url
OPENAI_COMPATIBLE_MODEL: str | None = settings.llm.openai_compatible_model

GOOGLE_API_KEY: str | None = settings.llm.google_api_key
DEFAULT_MODEL: str | None = settings.llm.default_model

EMBEDDING_MODEL: str = settings.embedding.model
EMBEDDING_DIM: int = settings.embedding.dim
EMBEDDING_DEVICE: str = settings.embedding.device

RAG_MARKDOWN_DIR: str = settings.rag.markdown_dir
RAG_OUTPUT_DIR: str = settings.rag.output_dir
RAG_MARKDOWN_COLLECTION: str = settings.rag.markdown_collection
RAG_ENTITY_COLLECTION: str = settings.rag.entity_collection
RAG_CHUNK_STRATEGY: str = settings.rag.chunk_strategy
RAG_CHUNK_MAX_TOKENS: int = settings.rag.chunk_max_tokens
RAG_CHUNK_OVERLAP_TOKENS: int = settings.rag.chunk_overlap_tokens
RAG_CHUNK_MIN_TOKENS: int = settings.rag.chunk_min_tokens

GRAPH_KEYWORD_MAX_TERMS: int = settings.graph.keyword_max_terms
GRAPH_KEYWORD_TIMEOUT_SECONDS: float = settings.graph.keyword_timeout_seconds
GRAPH_FULLTEXT_CANDIDATE_LIMIT: int = settings.graph.fulltext_candidate_limit
GRAPH_NEIGHBOR_LIMIT_PER_ENTITY: int = settings.graph.neighbor_limit_per_entity
GRAPH_FULLTEXT_ENTITY_INDEX: str = settings.graph.fulltext_entity_index
GRAPH_FULLTEXT_RELATIONSHIP_INDEX: str = settings.graph.fulltext_relationship_index
GRAPH_ENABLE_RELATIONSHIP_FULLTEXT: bool = settings.graph.enable_relationship_fulltext
GRAPH_ENABLE_SUBSTRING_FALLBACK: bool = settings.graph.enable_substring_fallback
GRAPH_SUBSTRING_FALLBACK_LIMIT: int = settings.graph.substring_fallback_limit
GRAPH_DESCRIPTION_FALLBACK_MIN_TERM_LENGTH: int = settings.graph.description_fallback_min_term_length
GRAPH_ALLOW_LEGACY_SCAN_FALLBACK: bool = settings.graph.allow_legacy_scan_fallback
GRAPHSEARCH_MAX_SUB_QUERIES: int = settings.graph.graphsearch_max_sub_queries
GRAPHSEARCH_MAX_EXPANDED_QUERIES: int = settings.graph.graphsearch_max_expanded_queries
GRAPH_ENTITY_SEARCH_TOP_K_MULTIPLIER: int = settings.graph.entity_search_top_k_multiplier
GRAPH_RELATIONSHIP_SEARCH_TOP_K_MULTIPLIER: int = settings.graph.relationship_search_top_k_multiplier
GRAPH_CONTEXT_ENTITY_TOP_K_MULTIPLIER: int = settings.graph.context_entity_top_k_multiplier
GRAPH_CONTEXT_RELATIONSHIP_TOP_K_MULTIPLIER: int = settings.graph.context_relationship_top_k_multiplier
GRAPH_CONTEXT_DESCRIPTION_MAX_CHARS: int = settings.graph.context_description_max_chars
GRAPH_SCORE_EXACT_NAME: float = settings.graph.score_exact_name
GRAPH_SCORE_EXACT_ALIAS: float = settings.graph.score_exact_alias
GRAPH_SCORE_PARTIAL_ALIAS: float = settings.graph.score_partial_alias
GRAPH_SCORE_PARTIAL_NAME: float = settings.graph.score_partial_name
GRAPH_SCORE_SEARCH_TEXT: float = settings.graph.score_search_text
GRAPH_SCORE_DESCRIPTION: float = settings.graph.score_description

RAGAS_SCORE_MAX_WORKERS: int = settings.evaluation.ragas_score_max_workers
RAGAS_SCORE_MAX_RETRIES: int = settings.evaluation.ragas_score_max_retries
RAGAS_SCORE_MAX_WAIT_SECONDS: int = settings.evaluation.ragas_score_max_wait_seconds
RAGAS_SCORE_TIMEOUT_SECONDS: int = settings.evaluation.ragas_score_timeout_seconds
RAGAS_LLM_TEMPERATURE: float = settings.evaluation.ragas_llm_temperature
QDRANT_UPSERT_BATCH_SIZE: int = settings.evaluation.qdrant_upsert_batch_size
OPENAI_API_KEY: str | None = settings.llm.openai_api_key
OPENAI_BASE_URL: str | None = settings.llm.openai_base_url
OPENAI_MODEL: str | None = settings.llm.openai_model
CX_API_KEY: str | None = settings.llm.cx_api_key
