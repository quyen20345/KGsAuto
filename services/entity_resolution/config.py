from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def _new_run_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"elv4_{ts}_{uuid4().hex[:6]}"


@dataclass
class RunConfig:
    input_dir: Path
    artifacts_dir: Path = Path("data/entity_resolution/artifacts")
    run_id: str = field(default_factory=_new_run_id)
    collection_name: str | None = None

    # Embedding configuration
    embedding_model: str = "paraphrase-multilingual-mpnet-base-v2"
    embedding_dim: int = 768  # Auto-detected from model if semantic

    # Clustering configuration
    min_cluster_size: int = 2
    min_samples: int = 1
    cluster_by_primary_type: bool = True
    cluster_similarity_threshold: float = 0.72

    # Fuzzy validation (PERSON only)
    enable_fuzzy_validation_person: bool = True
    min_name_similarity: float = 0.80
    min_alias_similarity: float = 0.50

    # Storage
    qdrant_url: str = "http://localhost:6333"
    store_backend: str = "qdrant"  # qdrant|memory

    # LLM Configuration (for LLM-CER)
    llm_provider: str = "proxypal"  # openai|anthropic|proxypal
    llm_model: str = "gpt-5"
    llm_api_key: str | None = None
    llm_temperature: float = 0.0
    llm_max_tokens: int = 2000

    # NRS parameters
    llm_set_size: int = 9  # Optimal record set size from paper
    llm_diversity: int = 4  # Target diversity
    llm_max_variation: float = 0.3  # Max size variation

    # MDG parameters
    mdg_similarity_threshold: float = 0.1  # From paper
    mdg_max_regenerations: int = 3  # Max retry attempts

    # CMR parameters
    cmr_merge_threshold: float = 0.80  # Similarity threshold for merging

    # Fallback strategy
    fallback_on_llm_failure: str = "skip"  # skip|merge_conservative

    def resolve_collection_name(self) -> str:
        if self.collection_name:
            return self.collection_name
        return f"{self.run_id}_vectors"

    def stage_dir(self, stage: str) -> Path:
        return self.artifacts_dir / self.run_id / stage
