"""Configuration for RAG System"""

from dataclasses import dataclass, field
from pathlib import Path
import os

from services.config import LLM_MODEL, LLM_PROVIDER, NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER, QDRANT_URL


@dataclass
class RAGConfig:
    """Configuration for RAG system"""

    # Data paths
    markdown_dir: Path = Path("data/raw/uet")
    output_dir: Path = Path("data/rag_system")

    # Qdrant configuration
    qdrant_url: str = field(default_factory=lambda: QDRANT_URL)
    markdown_collection: str = "rag_markdown_chunks"
    entity_collection: str = "rag_entities"

    # Neo4j configuration
    neo4j_uri: str = field(default_factory=lambda: NEO4J_URI)
    neo4j_user: str = field(default_factory=lambda: NEO4J_USER)
    neo4j_password: str = field(default_factory=lambda: NEO4J_PASSWORD)

    # Embedding configuration
    embedding_model: str = "paraphrase-multilingual-mpnet-base-v2"
    embedding_dim: int = 768
    embedding_batch_size: int = 32

    # Chunking configuration
    chunk_strategy: str = "section"  # section|semantic|fixed
    max_chunk_size: int = 512  # characters
    chunk_overlap: int = 50  # characters
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
    llm_temperature: float = 0.0
    llm_max_tokens: int = 2000

    # Fusion configuration
    fusion_strategy: str = "weighted"  # weighted|rrf|linear
    graph_weight: float = 0.6  # for relation/multi-hop queries
    markdown_weight: float = 0.4

    # GraphSearch keyword extraction
    graph_keyword_max_terms: int = field(default_factory=lambda: int(os.getenv("GRAPH_KEYWORD_MAX_TERMS", "12")))
    graph_keyword_timeout_seconds: float = field(default_factory=lambda: float(os.getenv("GRAPH_KEYWORD_TIMEOUT_SECONDS", "60.0")))

    # Evaluation configuration (based on user decision: 30 questions pilot)
    eval_pilot_size: int = 30  # Start with 30 questions
    eval_full_size: int = 100  # Expand later if needed
    eval_dataset: Path = Path("services/rag_system/evaluation/datasets/questions.json")
    eval_ground_truth: Path = Path("services/rag_system/evaluation/datasets/ground_truth.json")
    eval_output_dir: Path = Path("data/rag_system/evaluation/runs")

    def __post_init__(self):
        """Ensure paths are Path objects."""
        self.markdown_dir = Path(self.markdown_dir)
        self.output_dir = Path(self.output_dir)
        self.eval_dataset = Path(self.eval_dataset)
        self.eval_ground_truth = Path(self.eval_ground_truth)
        self.eval_output_dir = Path(self.eval_output_dir)
