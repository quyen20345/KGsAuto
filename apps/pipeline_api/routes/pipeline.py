import asyncio
import json

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from apps.pipeline_api.config import PROJECT_ROOT
from apps.pipeline_api.db import get_db
from apps.pipeline_api.models import (
    EntityResolutionStageRequest,
    IncrementalERRequest,
    ExtractStageRequest,
    PipelineRunDetail,
    PipelineRunRequest,
    PipelineRunResponse,
    StageCrawlRequest,
    StageCrawlResponse,
    StageUploadResponse,
)
from apps.pipeline_api import runner
from apps.pipeline_api.paths import safe_project_dir_path

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


def _workspace_display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT.resolve()))
    except ValueError:
        return str(path)


def _safe_upload_filename(filename: str | None) -> str | None:
    if not filename:
        return None
    path = Path(filename)
    if path.name != filename or filename in {".", ".."} or path.suffix.lower() != ".md":
        return None
    return filename


@router.post("/stages/upload")
async def upload_stage_files(
    output_dir: str = Form(...),
    files: list[UploadFile] = File(...),
) -> StageUploadResponse:
    destination_dir = safe_project_dir_path(output_dir, create=True)
    uploaded: list[str] = []
    skipped: list[str] = []

    for file in files:
        filename = _safe_upload_filename(file.filename)
        if not filename:
            skipped.append(file.filename or "unknown")
            continue

        destination = destination_dir / filename
        if destination.exists():
            skipped.append(filename)
            continue

        destination.write_bytes(await file.read())
        uploaded.append(filename)

    return StageUploadResponse(
        output_dir=_workspace_display_path(destination_dir),
        uploaded=uploaded,
        skipped=skipped,
    )


@router.post("/stages/crawl")
async def crawl_stage_urls(request: StageCrawlRequest) -> StageCrawlResponse:
    if not request.urls:
        raise HTTPException(status_code=400, detail="No URLs provided")

    output_dir = safe_project_dir_path(request.output_dir, create=True)

    from services.crawler.crawl_lib import crawl_urls

    files_created, errors = await asyncio.to_thread(crawl_urls, request.urls, output_dir)
    return StageCrawlResponse(
        output_dir=_workspace_display_path(output_dir),
        files_created=files_created,
        errors=errors,
    )


@router.post("/stages/extract")
async def run_extract_stage(request: ExtractStageRequest) -> PipelineRunResponse:
    input_dir = safe_project_dir_path(request.input_dir, must_exist=True)
    output_dir = safe_project_dir_path(request.output_dir, create=True)

    run_id = request.run_id or runner.generate_run_id()
    if not await runner.reserve_run(run_id):
        raise HTTPException(status_code=409, detail="A pipeline run is already in progress")

    asyncio.create_task(
        runner.execute_extract_stage(
            run_id,
            input_dir,
            output_dir,
            skip_existing=request.skip_existing,
        )
    )
    return PipelineRunResponse(run_id=run_id, status="pending")


@router.post("/stages/incremental-er")
async def run_incremental_er_stage(request: IncrementalERRequest) -> PipelineRunResponse:
    input_dir = safe_project_dir_path(request.input_dir, must_exist=True)

    run_id = request.run_id or runner.generate_run_id()
    if not await runner.reserve_run(run_id):
        raise HTTPException(status_code=409, detail="A pipeline run is already in progress")

    asyncio.create_task(
        runner.execute_incremental_er_stage(
            run_id,
            input_dir,
            candidate_top_k=request.candidate_top_k,
            candidate_min_score=request.candidate_min_score,
            enable_llm_blocking=request.enable_llm_blocking,
        )
    )
    return PipelineRunResponse(run_id=run_id, status="pending")


@router.post("/stages/entity-resolution")
async def run_entity_resolution_stage(request: EntityResolutionStageRequest) -> PipelineRunResponse:
    if request.store_backend not in {"memory", "qdrant"}:
        raise HTTPException(status_code=400, detail="store_backend must be 'memory' or 'qdrant'")

    input_dir = safe_project_dir_path(request.input_dir, must_exist=True)
    output_dir = safe_project_dir_path(request.output_dir, create=True)

    run_id = request.run_id or runner.generate_run_id()
    if not await runner.reserve_run(run_id):
        raise HTTPException(status_code=409, detail="A pipeline run is already in progress")

    asyncio.create_task(
        runner.execute_entity_resolution_stage(
            run_id,
            input_dir,
            output_dir,
            store_backend=request.store_backend,
        )
    )
    return PipelineRunResponse(run_id=run_id, status="pending")


@router.post("/run")
async def trigger_run(request: PipelineRunRequest) -> PipelineRunResponse:
    if request.mode not in ("quick_import", "full_pipeline"):
        raise HTTPException(status_code=400, detail="mode must be 'quick_import' or 'full_pipeline'")

    run_id = request.run_id or runner.generate_run_id()
    if not await runner.reserve_run(run_id):
        raise HTTPException(status_code=409, detail="A pipeline run is already in progress")

    asyncio.create_task(runner.execute_pipeline(run_id, request))
    return PipelineRunResponse(run_id=run_id, status="pending")


@router.get("/runs")
async def list_runs(limit: int = 20, offset: int = 0) -> list[PipelineRunDetail]:
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM pipeline_runs ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    results = []
    for row in rows:
        results.append(PipelineRunDetail(
            id=row["id"],
            status=row["status"],
            mode=row["mode"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            input_files=json.loads(row["input_files"]),
            current_step=row["current_step"],
            progress_pct=row["progress_pct"],
            error_message=row["error_message"],
        ))
    return results


@router.get("/runs/{run_id}")
async def get_run(run_id: str) -> dict:
    with get_db() as db:
        row = db.execute("SELECT * FROM pipeline_runs WHERE id = ?", (run_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Run not found")
        logs = db.execute(
            "SELECT timestamp, level, step, message FROM pipeline_logs WHERE run_id = ? ORDER BY id DESC LIMIT 100",
            (run_id,),
        ).fetchall()
    return {
        "run": PipelineRunDetail(
            id=row["id"],
            status=row["status"],
            mode=row["mode"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            input_files=json.loads(row["input_files"]),
            current_step=row["current_step"],
            progress_pct=row["progress_pct"],
            error_message=row["error_message"],
        ),
        "logs": [{"timestamp": l["timestamp"], "level": l["level"], "step": l["step"], "message": l["message"]} for l in reversed(logs)],
    }


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str):
    success = await runner.cancel_run(run_id)
    if not success:
        raise HTTPException(status_code=404, detail="Run not found or not active")
    return {"cancelled": True}
