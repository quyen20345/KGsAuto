from typing import Any, Literal

from pydantic import BaseModel, Field


class InitRunRequest(BaseModel):
    input_dir: str = Field(default="data/extracted_v2")
    score_threshold: float = 0.85
    limit: int = 10
    collection_name: str | None = None


class PairDecisionRequest(BaseModel):
    decision: Literal["MERGE", "SKIP"]
    canonical_id: str | None = None
    merged_properties: dict[str, Any] | None = None


class ApplyRequest(BaseModel):
    output_dir: str = Field(default="data/newgraph")


class ResetRequest(BaseModel):
    drop_collection: bool = True
