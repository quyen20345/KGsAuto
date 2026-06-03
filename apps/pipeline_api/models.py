from __future__ import annotations

from pydantic import BaseModel


class FileInfo(BaseModel):
    name: str
    size: int
    modified: str
    has_extraction: bool = False


class ExtractedFileInfo(BaseModel):
    name: str
    size: int
    modified: str
    node_count: int | None = None
    rel_count: int | None = None


class ERRunInfo(BaseModel):
    run_id: str
    has_stage1: bool = False
    has_stage2: bool = False
    has_stage3: bool = False
    output_file_count: int = 0


class UploadResponse(BaseModel):
    uploaded: list[str]
    skipped: list[str]


class PipelineRunRequest(BaseModel):
    files: list[str] | None = None
    mode: str = "full_pipeline"
    run_id: str | None = None


class PipelineRunResponse(BaseModel):
    run_id: str
    status: str


class PipelineRunDetail(BaseModel):
    id: str
    status: str
    mode: str
    created_at: str
    updated_at: str
    input_files: list[str]
    current_step: str | None = None
    progress_pct: int = 0
    error_message: str | None = None


class PipelineLogEntry(BaseModel):
    timestamp: str
    level: str
    step: str | None = None
    message: str


class CrawlRequest(BaseModel):
    urls: list[str]


class CrawlResponse(BaseModel):
    files_created: list[str]
    errors: list[str]


class StageUploadResponse(BaseModel):
    output_dir: str
    uploaded: list[str]
    skipped: list[str]


class StageCrawlRequest(BaseModel):
    urls: list[str]
    output_dir: str


class StageCrawlResponse(BaseModel):
    output_dir: str
    files_created: list[str]
    errors: list[str]


class ExtractStageRequest(BaseModel):
    input_dir: str
    output_dir: str
    skip_existing: bool = True
    run_id: str | None = None


class EntityResolutionStageRequest(BaseModel):
    input_dir: str
    output_dir: str
    store_backend: str = "memory"
    run_id: str | None = None



class IncrementalERRequest(BaseModel):
    input_dir: str
    candidate_top_k: int = 5
    candidate_min_score: float = 0.85
    enable_llm_blocking: bool = True
    run_id: str | None = None


class IncrementalERResult(BaseModel):
    run_id: str
    new_entities: int
    merged_entities: int
    total_clusters: int
    nodes_created: int
    nodes_updated: int
    relationships_created: int
    relationships_rewired: int
    embeddings_updated: int
    audit_path: str | None = None
