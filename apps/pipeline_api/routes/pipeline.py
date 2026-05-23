import asyncio
import json

from fastapi import APIRouter, HTTPException

from apps.pipeline_api.db import get_db
from apps.pipeline_api.models import PipelineRunDetail, PipelineRunRequest, PipelineRunResponse
from apps.pipeline_api import runner

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


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
