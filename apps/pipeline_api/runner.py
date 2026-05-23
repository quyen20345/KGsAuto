from __future__ import annotations

import asyncio
import json
import os
import shutil
import signal
import sys
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from apps.pipeline_api.config import EXTRACTED_DIR, ER_ARTIFACTS_DIR, PROJECT_ROOT, RAW_DIR
from apps.pipeline_api.db import get_db
from apps.pipeline_api.models import PipelineRunRequest
from apps.pipeline_api.paths import safe_raw_markdown_path

_active_process: asyncio.subprocess.Process | None = None
_active_run_id: str | None = None
_cancelling_run_id: str | None = None
_state_lock = asyncio.Lock()
_subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)


def is_busy() -> bool:
    return _active_run_id is not None


async def reserve_run(run_id: str) -> bool:
    global _active_run_id, _cancelling_run_id
    async with _state_lock:
        if _active_run_id is not None:
            return False
        _active_run_id = run_id
        _cancelling_run_id = None
        return True


async def _is_cancelled(run_id: str) -> bool:
    async with _state_lock:
        return _cancelling_run_id == run_id or _active_run_id != run_id


async def _clear_active_run(run_id: str):
    global _active_run_id, _active_process, _cancelling_run_id
    async with _state_lock:
        if _active_run_id == run_id:
            _active_run_id = None
            _active_process = None
            _cancelling_run_id = None


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


def _selected_input_dir(run_id: str, files: list[str] | None) -> Path:
    if not files:
        return RAW_DIR

    input_dir = PROJECT_ROOT / "data" / "pipeline_runs" / run_id / "input"
    if input_dir.exists():
        shutil.rmtree(input_dir)
    input_dir.mkdir(parents=True)

    for filename in files:
        source = safe_raw_markdown_path(filename)
        if not source.exists():
            raise FileNotFoundError(f"Selected file not found: {filename}")
        shutil.copy2(source, input_dir / source.name)

    return input_dir


async def _status(run_id: str, **event):
    await _broadcast(run_id, {"type": "status", **event})


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
        cwd=str(PROJECT_ROOT),
        start_new_session=True,
    )
    async with _state_lock:
        if _active_run_id == run_id:
            _active_process = proc
    await _stream_process(run_id, proc, step)
    await proc.wait()
    async with _state_lock:
        if _active_process is proc:
            _active_process = None
    return proc.returncode or 0


async def execute_pipeline(run_id: str, request: PipelineRunRequest):
    try:
        _create_run(run_id, request)
        await _status(run_id, status="pending", progress=0, progress_pct=0, current_step=None, error_message=None)

        input_dir = _selected_input_dir(run_id, request.files)
        mode = request.mode

        _update_run(run_id, status="extracting", current_step="extraction", progress_pct=10, error_message=None)
        await _status(run_id, status="extracting", progress=10, progress_pct=10, current_step="extraction", error_message=None)

        extract_args = ["-m", "services.extraction.cli", "--input-dir", str(input_dir), "--output-dir", str(EXTRACTED_DIR), "--skip-existing"]
        rc = await _run_subprocess(run_id, "extraction", extract_args)
        if await _is_cancelled(run_id):
            return
        if rc != 0:
            message = f"Extraction failed (exit code {rc})"
            _update_run(run_id, status="failed", error_message=message)
            await _status(run_id, status="failed", error=message, error_message=message, current_step="extraction")
            return

        if mode == "quick_import":
            # Step 2: Import directly from extracted
            _update_run(run_id, status="importing", current_step="neo4j_import", progress_pct=60)
            await _status(run_id, status="importing", progress=60, progress_pct=60, current_step="neo4j_import")

            import_args = ["-m", "services.neo4j_import.import_to_neo4j", "--dir", str(EXTRACTED_DIR)]
            rc = await _run_subprocess(run_id, "neo4j_import", import_args)
            if await _is_cancelled(run_id):
                return
            if rc != 0:
                message = f"Import failed (exit code {rc})"
                _update_run(run_id, status="failed", error_message=message)
                await _status(run_id, status="failed", error=message, error_message=message, current_step="neo4j_import")
                return

        else:
            # Step 2: Entity Resolution
            _update_run(run_id, status="resolving", current_step="entity_resolution", progress_pct=30)
            await _status(run_id, status="resolving", progress=30, progress_pct=30, current_step="entity_resolution")

            er_args = ["-m", "services.entity_resolution.cli", "--stage", "all", "--input-dir", str(EXTRACTED_DIR), "--store-backend", "qdrant", "--run-id", run_id]
            rc = await _run_subprocess(run_id, "entity_resolution", er_args)
            if await _is_cancelled(run_id):
                return
            if rc != 0:
                message = f"Entity resolution failed (exit code {rc})"
                _update_run(run_id, status="failed", error_message=message)
                await _status(run_id, status="failed", error=message, error_message=message, current_step="entity_resolution")
                return

            _update_run(run_id, status="importing", current_step="neo4j_import", progress_pct=80)
            await _status(run_id, status="importing", progress=80, progress_pct=80, current_step="neo4j_import")

            output_dir = ER_ARTIFACTS_DIR / run_id / "stage3" / "output_graph"
            import_args = ["-m", "services.neo4j_import.import_to_neo4j", "--dir", str(output_dir)]
            rc = await _run_subprocess(run_id, "neo4j_import", import_args)
            if await _is_cancelled(run_id):
                return
            if rc != 0:
                message = f"Import failed (exit code {rc})"
                _update_run(run_id, status="failed", error_message=message)
                await _status(run_id, status="failed", error=message, error_message=message, current_step="neo4j_import")
                return

        _update_run(run_id, status="completed", progress_pct=100, current_step=None)
        await _status(run_id, status="completed", progress=100, progress_pct=100, current_step=None)

    except asyncio.CancelledError:
        _update_run(run_id, status="failed", error_message="Cancelled by user")
        await _status(run_id, status="failed", error="Cancelled", error_message="Cancelled by user")
    except Exception as e:
        _update_run(run_id, status="failed", error_message=str(e))
        await _status(run_id, status="failed", error=str(e), error_message=str(e))
    finally:
        await _clear_active_run(run_id)


async def cancel_run(run_id: str) -> bool:
    global _cancelling_run_id
    async with _state_lock:
        if _active_run_id != run_id:
            return False
        _cancelling_run_id = run_id
        proc = _active_process

    if proc and proc.returncode is None:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            await asyncio.wait_for(proc.wait(), timeout=5)
        except asyncio.TimeoutError:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            await proc.wait()

    _update_run(run_id, status="failed", error_message="Cancelled by user")
    await _status(run_id, status="failed", error="Cancelled", error_message="Cancelled by user")
    return True


def generate_run_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    short = uuid.uuid4().hex[:6]
    return f"run_{ts}_{short}"
