from pydantic import BaseModel, Field


class QueryModel(BaseModel):
    cypher: str


class MergeEntityModel(BaseModel):
    canonical_id: str = Field(..., min_length=1)
    merge_ids: list[str] = Field(..., min_length=1)


class MergeEntityResponse(BaseModel):
    success: bool
    data: dict | None = None
    error: str | None = None
