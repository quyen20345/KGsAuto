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
