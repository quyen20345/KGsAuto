"""Public orchestration entrypoints for entity resolution.

The stage implementations live under :mod:`services.entity_resolution.pipelines`.
This module is the stable import surface for callers and the CLI.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from .config import RunConfig
from .pipelines.stage1_pipeline import run_stage1
from .pipelines.stage2_pipeline import run_stage2
from .pipelines.stage3_pipeline import run_stage3
from .types import Stage1Result, Stage2Result, Stage3Result


EntityResolutionStage = Literal["stage1", "stage2", "stage3", "all"]


@dataclass
class EntityResolutionResult:
    """Result envelope returned by the public entity-resolution pipeline."""

    run_id: str
    stage1: Stage1Result | None = None
    stage2: Stage2Result | None = None
    stage3: Stage3Result | None = None

    def to_dict(self) -> dict:
        outputs = {
            stage: asdict(result)
            for stage, result in {
                "stage1": self.stage1,
                "stage2": self.stage2,
                "stage3": self.stage3,
            }.items()
            if result is not None
        }
        return {"run_id": self.run_id, "outputs": outputs}


def run_entity_resolution(config: RunConfig, stage: EntityResolutionStage = "all") -> EntityResolutionResult:
    """Run one or all entity-resolution stages with a shared config.

    When ``config.store_backend == "memory"``, callers should use ``stage="all"``
    because the in-memory vector store is not persistent between processes.
    """

    if stage not in {"stage1", "stage2", "stage3", "all"}:
        raise ValueError(f"Unsupported entity-resolution stage: {stage}")

    result = EntityResolutionResult(run_id=config.run_id)
    if stage in {"stage1", "all"}:
        result.stage1 = run_stage1(config)
    if stage in {"stage2", "all"}:
        result.stage2 = run_stage2(config)
    if stage in {"stage3", "all"}:
        result.stage3 = run_stage3(config)
    return result


__all__ = [
    "EntityResolutionResult",
    "EntityResolutionStage",
    "run_entity_resolution",
    "run_stage1",
    "run_stage2",
    "run_stage3",
]
