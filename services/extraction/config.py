"""Configuration for Knowledge Graph Extraction Service"""

from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime

from services.config import settings


def _new_run_id() -> str:
    """Generate a unique run ID based on timestamp"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


@dataclass
class ExtractionConfig:
    """Configuration for extraction pipeline"""

    # Input/Output
    input_dir: Path
    output_dir: Path

    # LLM Configuration
    provider: str = settings.llm.provider
    model_name: str = settings.llm.model

    # Extraction Behavior
    max_retries: int = 3
    save_failed: bool = True
    skip_existing: bool = True

    # Layered context behavior
    context_char_budget: int = 4000
    core_pack_enabled: bool = True
    local_context_enabled: bool = True
    rolling_summary_enabled: bool = True
    one_file_per_chunk: bool = True
    local_context_top_k: int = 5
    truncation_suffix: str = "...(truncated)"
    cluster_similarity_threshold: float = 0.3
    cluster_max_workers: int = 1
    rolling_summary_max_items: int = 20
    core_pack_text: str = (
        "Use stable canonical entity names when the text supports them.\n"
        "Keep aliases concise and reuse prior names when they clearly refer to the same entity.\n"
        "Prefer consistent naming for UET and ĐHQGHN across related files."
    )
    summary_fact_prefix: str = "Recent cluster facts"

    # Execution behavior
    random_seed: int = 42
    progress_log_every: int = 10

    # Directories
    failed_dir: Path = Path("data/failed_responses")

    # Run Metadata
    run_id: str = field(default_factory=_new_run_id)

    def __post_init__(self):
        """Convert string paths to Path objects"""
        self.input_dir = Path(self.input_dir)
        self.output_dir = Path(self.output_dir)
        self.failed_dir = Path(self.failed_dir)

        # Create directories if they don't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if self.save_failed:
            self.failed_dir.mkdir(parents=True, exist_ok=True)

    def log_file_path(self) -> Path:
        """Get path for log file"""
        return self.output_dir / f"extraction_{self.run_id}.log"

    def summary_file_path(self) -> Path:
        """Get path for summary report"""
        return self.output_dir / f"extraction_summary_{self.run_id}.json"
