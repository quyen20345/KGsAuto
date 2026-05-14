"""Configuration for RAG System"""

from dataclasses import dataclass, field
from pathlib import Path

from services.config import (
    EMBEDDING_DEVICE,
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    GRAPH_ALLOW_LEGACY_SCAN_FALLBACK,
    GRAPH_CONTEXT_DESCRIPTION_MAX_CHARS,
    GRAPH_CONTEXT_ENTITY_TOP_K_MULTIPLIER,
    GRAPH_CONTEXT_RELATIONSHIP_TOP_K_MULTIPLIER,
    GRAPH_DESCRIPTION_FALLBACK_MIN_TERM_LENGTH,
    GRAPH_ENABLE_RELATIONSHIP_FULLTEXT,
    GRAPH_ENABLE_SUBSTRING_FALLBACK,
    GRAPH_ENTITY_SEARCH_TOP_K_MULTIPLIER,
    GRAPH_FULLTEXT_CANDIDATE_LIMIT,
    GRAPH_FULLTEXT_ENTITY_INDEX,
    GRAPH_FULLTEXT_RELATIONSHIP_INDEX,
    GRAPH_KEYWORD_MAX_TERMS,
    GRAPH_KEYWORD_TIMEOUT_SECONDS,
    GRAPH_NEIGHBOR_LIMIT_PER_ENTITY,
    GRAPH_RELATIONSHIP_SEARCH_TOP_K_MULTIPLIER,
    GRAPH_SCORE_DESCRIPTION,
    GRAPH_SCORE_EXACT_ALIAS,
    GRAPH_SCORE_EXACT_NAME,
    GRAPH_SCORE_PARTIAL_ALIAS,
    GRAPH_SCORE_PARTIAL_NAME,
    GRAPH_SCORE_SEARCH_TEXT,
    GRAPH_SUBSTRING_FALLBACK_LIMIT,
    LLM_MODEL,
    LLM_PROVIDER,
    NEO4J_PASSWORD,
    NEO4J_URI,
    NEO4J_USER,
    QDRANT_URL,
    RAG_CHUNK_MAX_TOKENS,
    RAG_CHUNK_MIN_TOKENS,
    RAG_CHUNK_OVERLAP_TOKENS,
    RAG_CHUNK_STRATEGY,
    RAG_ENTITY_COLLECTION,
    RAG_MARKDOWN_COLLECTION,
    RAG_MARKDOWN_DIR,
    RAG_OUTPUT_DIR,
)


@dataclass
class RAGConfig:
    """Configuration for RAG system"""

    # Data paths
    markdown_dir: Path = Path(RAG_MARKDOWN_DIR)
    output_dir: Path = Path(RAG_OUTPUT_DIR)

    # Qdrant configuration
    qdrant_url: str = field(default_factory=lambda: QDRANT_URL)
    markdown_collection: str = RAG_MARKDOWN_COLLECTION
    entity_collection: str = RAG_ENTITY_COLLECTION

    # Neo4j configuration
    neo4j_uri: str = field(default_factory=lambda: NEO4J_URI)
    neo4j_user: str = field(default_factory=lambda: NEO4J_USER)
    neo4j_password: str = field(default_factory=lambda: NEO4J_PASSWORD)

    # Embedding configuration
    embedding_model: str = EMBEDDING_MODEL
    embedding_dim: int = EMBEDDING_DIM
    embedding_device: str = EMBEDDING_DEVICE
    embedding_batch_size: int = 32

    # Chunking configuration
    chunk_strategy: str = RAG_CHUNK_STRATEGY  # section|fixed|sentence
    chunk_max_tokens: int = RAG_CHUNK_MAX_TOKENS
    chunk_overlap_tokens: int = RAG_CHUNK_OVERLAP_TOKENS
    chunk_min_tokens: int = RAG_CHUNK_MIN_TOKENS
    max_chunk_size: int = 512  # deprecated: character-based legacy setting
    chunk_overlap: int = 50  # deprecated: character-based legacy setting
    context_enrichment: bool = True  # prepend title/section to chunk text
    recursive_chunking: bool = True  # use hierarchical splitting (headers -> paragraphs)

    # Retrieval configuration
    top_k_markdown: int = 5
    top_k_graph: int = 5
    max_graph_depth: int = 1  # 1-hop default, 2-hop for multi-hop
    max_relations: int = 20

    # LLM configuration
    llm_provider: str = field(default_factory=lambda: LLM_PROVIDER)
    llm_model: str = field(default_factory=lambda: LLM_MODEL)
    llm_temperature: float = 0.3
    llm_max_tokens: int = 2000

    # Fusion configuration
    fusion_strategy: str = "weighted"  # weighted|rrf|linear
    graph_weight: float = 0.6  # for relation/multi-hop queries
    markdown_weight: float = 0.4

    # GraphSearch retrieval
    graph_keyword_max_terms: int = field(default_factory=lambda: GRAPH_KEYWORD_MAX_TERMS)
    graph_keyword_timeout_seconds: float = field(default_factory=lambda: GRAPH_KEYWORD_TIMEOUT_SECONDS)
    graph_fulltext_candidate_limit: int = field(default_factory=lambda: GRAPH_FULLTEXT_CANDIDATE_LIMIT)
    graph_neighbor_limit_per_entity: int = field(default_factory=lambda: GRAPH_NEIGHBOR_LIMIT_PER_ENTITY)
    graph_fulltext_entity_index: str = field(default_factory=lambda: GRAPH_FULLTEXT_ENTITY_INDEX)
    graph_fulltext_relationship_index: str = field(default_factory=lambda: GRAPH_FULLTEXT_RELATIONSHIP_INDEX)
    graph_enable_relationship_fulltext: bool = field(default_factory=lambda: GRAPH_ENABLE_RELATIONSHIP_FULLTEXT)
    graph_enable_substring_fallback: bool = field(default_factory=lambda: GRAPH_ENABLE_SUBSTRING_FALLBACK)
    graph_substring_fallback_limit: int = field(default_factory=lambda: GRAPH_SUBSTRING_FALLBACK_LIMIT)
    graph_description_fallback_min_term_length: int = field(
        default_factory=lambda: GRAPH_DESCRIPTION_FALLBACK_MIN_TERM_LENGTH
    )
    graph_allow_legacy_scan_fallback: bool = field(default_factory=lambda: GRAPH_ALLOW_LEGACY_SCAN_FALLBACK)

    # GraphSearch context sizing
    graph_entity_search_top_k_multiplier: int = field(default_factory=lambda: GRAPH_ENTITY_SEARCH_TOP_K_MULTIPLIER)
    graph_relationship_search_top_k_multiplier: int = field(default_factory=lambda: GRAPH_RELATIONSHIP_SEARCH_TOP_K_MULTIPLIER)
    graph_context_entity_top_k_multiplier: int = field(default_factory=lambda: GRAPH_CONTEXT_ENTITY_TOP_K_MULTIPLIER)
    graph_context_relationship_top_k_multiplier: int = field(default_factory=lambda: GRAPH_CONTEXT_RELATIONSHIP_TOP_K_MULTIPLIER)
    graph_context_description_max_chars: int = field(default_factory=lambda: GRAPH_CONTEXT_DESCRIPTION_MAX_CHARS)

    # GraphSearch scoring weights
    graph_score_exact_name: float = field(default_factory=lambda: GRAPH_SCORE_EXACT_NAME)
    graph_score_exact_alias: float = field(default_factory=lambda: GRAPH_SCORE_EXACT_ALIAS)
    graph_score_partial_alias: float = field(default_factory=lambda: GRAPH_SCORE_PARTIAL_ALIAS)
    graph_score_partial_name: float = field(default_factory=lambda: GRAPH_SCORE_PARTIAL_NAME)
    graph_score_search_text: float = field(default_factory=lambda: GRAPH_SCORE_SEARCH_TEXT)
    graph_score_description: float = field(default_factory=lambda: GRAPH_SCORE_DESCRIPTION)

    # Evaluation configuration (based on user decision: 30 questions pilot)
    eval_pilot_size: int = 30  # Start with 30 questions
    eval_full_size: int = 100  # Expand later if needed
    eval_dataset: Path = Path("services/rag_system/evaluation/datasets/questions.json")
    eval_ground_truth: Path = Path("services/rag_system/evaluation/datasets/ground_truth.json")
    eval_output_dir: Path = Path("data/rag_system/evaluation/runs")

    def __post_init__(self):
        """Ensure paths are Path objects."""
        if self.chunk_overlap >= self.max_chunk_size:
            raise ValueError("chunk_overlap must be smaller than max_chunk_size")
        if self.chunk_overlap_tokens >= self.chunk_max_tokens:
            raise ValueError("chunk_overlap_tokens must be smaller than chunk_max_tokens")
        if self.chunk_min_tokens >= self.chunk_max_tokens:
            raise ValueError("chunk_min_tokens must be smaller than chunk_max_tokens")
        self.markdown_dir = Path(self.markdown_dir)
        self.output_dir = Path(self.output_dir)
        self.eval_dataset = Path(self.eval_dataset)
        self.eval_ground_truth = Path(self.eval_ground_truth)
        self.eval_output_dir = Path(self.eval_output_dir)
