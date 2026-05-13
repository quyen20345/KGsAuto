from __future__ import annotations

import asyncio
import json
import sys
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from apps.pipeline_api.config import EXTRACTED_DIR, ER_ARTIFACTS_DIR, RAW_DIR
from apps.pipeline_api.db import get_db
from apps.pipeline_api.models import PipelineRunRequest

_active_process: asyncio.subprocess.Process | None = None
_active_run_id: str | None = None
_subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)


def is_busy() -> bool:
    return _active_run_id is not None


def subscribe(run_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _subscribers[run_id].append(q)
    return q


def unsubscribe(run_id: str, q: asyncio.Queue):
    subs = _subscribers.get(run_id, [])
    if q in subs:
        subs.remove(q)
    if not subs:
        _subscribers.pop(run_id, None)


async def _broadcast(run_id: str, event: dict):
    for q in _subscribers.get(run_id, []):
        await q.put(event)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _create_run(run_id: str, request: PipelineRunRequest):
    with get_db() as db:
        db.execute(
            "INSERT INTO pipeline_runs (id, status, mode, created_at, updated_at, input_files, config) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (run_id, "pending", request.mode, _now(), _now(), json.dumps(request.files or []), json.dumps({"mode": request.mode})),
        )


def _update_run(run_id: str, **kwargs):
    kwargs["updated_at"] = _now()
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [run_id]
    with get_db() as db:
        db.execute(f"UPDATE pipeline_runs SET {sets} WHERE id = ?", vals)


def _add_log(run_id: str, level: str, message: str, step: str | None = None):
    with get_db() as db:
        db.execute(
            "INSERT INTO pipeline_logs (run_id, timestamp, level, step, message) VALUES (?, ?, ?, ?, ?)",
            (run_id, _now(), level, step, message),
        )


async def _stream_process(run_id: str, proc: asyncio.subprocess.Process, step: str):
    assert proc.stdout is not None
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        text = line.decode(errors="replace").rstrip()
        _add_log(run_id, "info", text, step)
        await _broadcast(run_id, {"type": "log", "step": step, "message": text})


async def _run_subprocess(run_id: str, step: str, args: list[str]) -> int:
    global _active_process
    proc = await asyncio.create_subprocess_exec(
        sys.executable, *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=str(RAW_DIR.parent.parent.parent),
    )
    _active_process = proc
    await _stream_process(run_id, proc, step)
    await proc.wait()
    _active_process = None
    return proc.returncode or 0


async def execute_pipeline(run_id: str, request: PipelineRunRequest):
    global _active_run_id
    _active_run_id = run_id

    try:
        _create_run(run_id, request)
        await _broadcast(run_id, {"type": "status", "status": "pending", "progress": 0})

        input_files = request.files
        mode = request.mode

        # Step 1: Extraction
        _update_run(run_id, status="extracting", current_step="extraction", progress_pct=10)
        await _broadcast(run_id, {"type": "status", "status": "extracting", "progress": 10})

        extract_args = ["-m", "services.extraction.cli", "--input-dir", str(RAW_DIR), "--output-dir", str(EXTRACTED_DIR), "--skip-existing"]
        rc = await _run_subprocess(run_id, "extraction", extract_args)
        if rc != 0:
            _update_run(run_id, status="failed", error_message=f"Extraction failed (exit code {rc})")
            await _broadcast(run_id, {"type": "status", "status": "failed", "error": f"Extraction failed (exit code {rc})"})
            return

        if mode == "quick_import":
            # Step 2: Import directly from extracted
            _update_run(run_id, status="importing", current_step="neo4j_import", progress_pct=60)
            await _broadcast(run_id, {"type": "status", "status": "importing", "progress": 60})

            import_args = ["-m", "services.neo4j_import.import_to_neo4j", "--dir", str(EXTRACTED_DIR)]
            rc = await _run_subprocess(run_id, "neo4j_import", import_args)
            if rc != 0:
                _update_run(run_id, status="failed", error_message=f"Import failed (exit code {rc})")
                await _broadcast(run_id, {"type": "status", "status": "failed", "error": f"Import failed (exit code {rc})"})
                return

        else:
            # Step 2: Entity Resolution
            _update_run(run_id, status="resolving", current_step="entity_resolution", progress_pct=30)
            await _broadcast(run_id, {"type": "status", "status": "resolving", "progress": 30})

            er_args = ["-m", "services.entity_resolution.cli", "--stage", "all", "--input-dir", str(EXTRACTED_DIR), "--store-backend", "qdrant", "--run-id", run_id]
            rc = await _run_subprocess(run_id, "entity_resolution", er_args)
            if rc != 0:
                _update_run(run_id, status="failed", error_message=f"Entity resolution failed (exit code {rc})")
                await _broadcast(run_id, {"type": "status", "status": "failed", "error": f"Entity resolution failed (exit code {rc})"})
                return

            # Step 3: Import from ER output
            _update_run(run_id, status="importing", current_step="neo4j_import", progress_pct=80)
            await _broadcast(run_id, {"type": "status", "status": "importing", "progress": 80})

            output_dir = ER_ARTIFACTS_DIR / run_id / "stage3" / "output_graph"
            import_args = ["-m", "services.neo4j_import.import_to_neo4j", "--dir", str(output_dir)]
            rc = await _run_subprocess(run_id, "neo4j_import", import_args)
            if rc != 0:
                _update_run(run_id, status="failed", error_message=f"Import failed (exit code {rc})")
                await _broadcast(run_id, {"type": "status", "status": "failed", "error": f"Import failed (exit code {rc})"})
                return

        _update_run(run_id, status="completed", progress_pct=100, current_step=None)
        await _broadcast(run_id, {"type": "status", "status": "completed", "progress": 100})

    except asyncio.CancelledError:
        _update_run(run_id, status="failed", error_message="Cancelled by user")
        await _broadcast(run_id, {"type": "status", "status": "failed", "error": "Cancelled"})
    except Exception as e:
        _update_run(run_id, status="failed", error_message=str(e))
        await _broadcast(run_id, {"type": "status", "status": "failed", "error": str(e)})
    finally:
        _active_run_id = None


async def cancel_run(run_id: str) -> bool:
    global _active_process, _active_run_id
    if _active_run_id != run_id:
        return False
    if _active_process and _active_process.returncode is None:
        _active_process.terminate()
    _active_run_id = None
    _update_run(run_id, status="failed", error_message="Cancelled by user")
    await _broadcast(run_id, {"type": "status", "status": "failed", "error": "Cancelled"})
    return True


def generate_run_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    short = uuid.uuid4().hex[:6]
    return f"run_{ts}_{short}"
