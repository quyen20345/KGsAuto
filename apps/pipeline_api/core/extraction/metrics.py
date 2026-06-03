"""Metrics tracking for extraction pipeline"""

from dataclasses import dataclass, asdict
from typing import Dict, Any
import json
from pathlib import Path


@dataclass
class ExtractionMetrics:
    """Metrics for extraction pipeline execution"""

    # File counts
    total_files: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0

    # Entity counts
    total_nodes: int = 0
    total_relationships: int = 0

    # Resource usage
    total_tokens: int = 0
    total_processing_time: float = 0.0

    # Averages (computed)
    avg_nodes_per_file: float = 0.0
    avg_relationships_per_file: float = 0.0
    avg_tokens_per_file: float = 0.0
    avg_processing_time: float = 0.0

    def compute_averages(self):
        """Compute average metrics based on successful extractions"""
        if self.successful > 0:
            self.avg_nodes_per_file = self.total_nodes / self.successful
            self.avg_relationships_per_file = self.total_relationships / self.successful
            self.avg_tokens_per_file = self.total_tokens / self.successful
            self.avg_processing_time = self.total_processing_time / self.successful

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return asdict(self)

    def save_to_file(self, file_path: Path):
        """Save metrics to JSON file"""
        self.compute_averages()
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    def __str__(self) -> str:
        """String representation for logging"""
        self.compute_averages()
        return f"""
Extraction Metrics:
  Files: {self.successful}/{self.total_files} successful ({self.failed} failed, {self.skipped} skipped)
  Entities: {self.total_nodes} nodes, {self.total_relationships} relationships
  Tokens: {self.total_tokens} total ({self.avg_tokens_per_file:.1f} avg/file)
  Processing Time: {self.total_processing_time:.2f}s total ({self.avg_processing_time:.2f}s avg/file)
  Avg per file: {self.avg_nodes_per_file:.1f} nodes, {self.avg_relationships_per_file:.1f} relationships
"""
