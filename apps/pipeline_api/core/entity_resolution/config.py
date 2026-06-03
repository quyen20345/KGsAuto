from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from apps.pipeline_api.config import EMBEDDING_DIM, EMBEDDING_MODEL
from apps.pipeline_api.core.config import settings


def _new_run_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"incremental_er_{ts}_{uuid4().hex[:6]}"


@dataclass
class ERConfig:
    input_dir: Path
    artifacts_dir: Path = Path("data/entity_resolution/artifacts")
    run_id: str = field(default_factory=_new_run_id)

    embedding_model: str = EMBEDDING_MODEL
    embedding_dim: int = EMBEDDING_DIM

    min_cluster_size: int = 2
    min_samples: int = 1
    cluster_similarity_threshold: float = 0.72
    enable_llm_blocking: bool = True

    llm_provider: str = settings.llm.provider
    llm_model: str = settings.llm.model
    llm_api_key: str | None = None
    conservative_merge_threshold: float = 0.88

    candidate_top_k: int = 5
    candidate_min_score: float = 0.85

    def stage_dir(self, stage: str) -> Path:
        return self.artifacts_dir / self.run_id / stage


RunConfig = ERConfig


@dataclass
class IncrementalERResult:
    run_id: str
    new_entities: int = 0
    merged_entities: int = 0
    total_clusters: int = 0
    nodes_created: int = 0
    nodes_updated: int = 0
    relationships_created: int = 0
    relationships_rewired: int = 0
    embeddings_updated: int = 0
    audit_path: str | None = None

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "new_entities": self.new_entities,
            "merged_entities": self.merged_entities,
            "total_clusters": self.total_clusters,
            "nodes_created": self.nodes_created,
            "nodes_updated": self.nodes_updated,
            "relationships_created": self.relationships_created,
            "relationships_rewired": self.relationships_rewired,
            "embeddings_updated": self.embeddings_updated,
            "audit_path": self.audit_path,
        }
