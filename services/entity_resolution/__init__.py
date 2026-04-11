"""Entity Resolution pipeline package."""

from .config import RunConfig
from .pipelines.stage1_pipeline import run_stage1
from .pipelines.stage2_pipeline import run_stage2
from .pipelines.stage3_pipeline import run_stage3

__all__ = ["RunConfig", "run_stage1", "run_stage2", "run_stage3"]
