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
from apps.pipeline_api.core.extraction import run_extraction
from apps.pipeline_api.core.entity_resolution import run_incremental_entity_resolution
from apps.pipeline_api.core.neo4j import get_neo4j_driver
from apps.pipeline_api.core.neo4j_vector import Neo4jVectorService
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


def _is_cancelled_now(run_id: str) -> bool:
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


def _create_stage_run(run_id: str, mode: str, input_files: list[str], config: dict):
    with get_db() as db:
        db.execute(
            "INSERT INTO pipeline_runs (id, status, mode, created_at, updated_at, input_files, config) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (run_id, "pending", mode, _now(), _now(), json.dumps(input_files), json.dumps(config)),
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


def _count_graph_dir(graph_dir: Path) -> dict[str, int]:
    metrics = {"files": 0, "nodes": 0, "relationships": 0}
    if not graph_dir.exists() or not graph_dir.is_dir():
        return metrics

    for path in sorted(graph_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        metrics["files"] += 1
        metrics["nodes"] += len(data.get("nodes") or [])
        metrics["relationships"] += len(data.get("relationships") or [])
    return metrics


def _workspace_display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT.resolve()))
    except ValueError:
        return str(path)


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


async def execute_extract_stage(run_id: str, input_dir: Path, output_dir: Path, *, skip_existing: bool = True):
    input_files = [path.name for path in sorted(input_dir.rglob("*.md"), key=lambda path: str(path.relative_to(input_dir)))]
    try:
        _create_stage_run(
            run_id,
            "extract_stage",
            input_files,
            {
                "stage": "extraction",
                "input_dir": str(input_dir),
                "output_dir": str(output_dir),
                "skip_existing": skip_existing,
            },
        )
        await _status(run_id, status="pending", progress=0, progress_pct=0, current_step=None, error_message=None)

        _update_run(run_id, status="extracting", current_step="extraction", progress_pct=0, error_message=None)
        await _status(
            run_id,
            status="extracting",
            progress=0,
            progress_pct=0,
            current_step="extraction",
            input_dir=str(input_dir),
            output_dir=str(output_dir),
            error_message=None,
        )

        selected_files = sorted(input_dir.rglob("*.md"), key=lambda path: str(path.relative_to(input_dir)))

        async def on_extraction_progress(event: dict):
            if await _is_cancelled(run_id):
                return

            pct = int(event.get("progress_pct") or 0)
            pct = max(0, min(100, pct))
            processed = event.get("processed") or 0
            total = event.get("total") or 0

            _update_run(run_id, status="extracting", current_step="extraction", progress_pct=pct)
            _add_log(
                run_id,
                "info",
                f"[{processed}/{total}] {event.get('status')}: {event.get('file')}",
                "extraction",
            )
            await _status(
                run_id,
                status="extracting",
                progress=pct,
                progress_pct=pct,
                current_step="extraction",
                file=event.get("file"),
                file_status=event.get("status"),
                input_dir=str(input_dir),
                output_dir=str(output_dir),
                extraction=event,
            )

        await run_extraction(
            input_dir=input_dir,
            output_dir=output_dir,
            files=selected_files,
            run_id=run_id,
            progress_callback=on_extraction_progress,
            should_cancel=lambda: _is_cancelled_now(run_id),
            skip_existing=skip_existing,
            failed_dir=output_dir / "failed_responses",
        )
        if await _is_cancelled(run_id):
            return

        _update_run(run_id, status="completed", progress_pct=100, current_step=None)
        await _status(
            run_id,
            status="completed",
            progress=100,
            progress_pct=100,
            current_step=None,
            input_dir=str(input_dir),
            output_dir=str(output_dir),
        )

    except asyncio.CancelledError:
        _update_run(run_id, status="failed", error_message="Cancelled by user")
        await _status(run_id, status="failed", error="Cancelled", error_message="Cancelled by user")
    except Exception as e:
        _update_run(run_id, status="failed", current_step="extraction", error_message=str(e))
        await _status(run_id, status="failed", error=str(e), error_message=str(e), current_step="extraction")
    finally:
        await _clear_active_run(run_id)


async def execute_entity_resolution_stage(
    run_id: str,
    input_dir: Path,
    output_dir: Path,
    *,
    store_backend: str = "memory",
):
    input_files = [path.name for path in sorted(input_dir.glob("*.json"))]
    er_run_id = output_dir.name
    artifacts_dir = output_dir.parent
    output_graph_dir = output_dir / "stage3" / "output_graph"

    try:
        _create_stage_run(
            run_id,
            "entity_resolution_stage",
            input_files,
            {
                "stage": "entity_resolution",
                "input_dir": str(input_dir),
                "output_dir": str(output_dir),
                "artifacts_dir": str(artifacts_dir),
                "er_run_id": er_run_id,
                "store_backend": store_backend,
            },
        )
        await _status(run_id, status="pending", progress=0, progress_pct=0, current_step=None, error_message=None)

        _update_run(run_id, status="resolving", current_step="entity_resolution", progress_pct=5, error_message=None)
        await _status(
            run_id,
            status="resolving",
            progress=5,
            progress_pct=5,
            current_step="entity_resolution",
            input_dir=str(input_dir),
            output_dir=str(output_dir),
            output_graph_dir=str(output_graph_dir),
            store_backend=store_backend,
            error_message=None,
        )

        er_args = [
            "-m",
            "services.entity_resolution.cli",
            "--stage",
            "all",
            "--input-dir",
            str(input_dir),
            "--artifacts-dir",
            str(artifacts_dir),
            "--run-id",
            er_run_id,
            "--store-backend",
            store_backend,
        ]
        rc = await _run_subprocess(run_id, "entity_resolution", er_args)
        if await _is_cancelled(run_id):
            return
        if rc != 0:
            message = f"Entity resolution failed (exit code {rc})"
            _update_run(run_id, status="failed", current_step="entity_resolution", error_message=message)
            await _status(run_id, status="failed", error=message, error_message=message, current_step="entity_resolution")
            return

        metrics = _count_graph_dir(output_graph_dir)
        _update_run(run_id, status="completed", progress_pct=100, current_step=None)
        await _status(
            run_id,
            status="completed",
            progress=100,
            progress_pct=100,
            current_step=None,
            input_dir=str(input_dir),
            output_dir=_workspace_display_path(output_dir),
            output_graph_dir=_workspace_display_path(output_graph_dir),
            entity_resolution={
                "files": metrics["files"],
                "nodes": metrics["nodes"],
                "relationships": metrics["relationships"],
                "store_backend": store_backend,
            },
        )

    except asyncio.CancelledError:
        _update_run(run_id, status="failed", error_message="Cancelled by user")
        await _status(run_id, status="failed", error="Cancelled", error_message="Cancelled by user")
    except Exception as e:
        _update_run(run_id, status="failed", current_step="entity_resolution", error_message=str(e))
        await _status(run_id, status="failed", error=str(e), error_message=str(e), current_step="entity_resolution")
    finally:
        await _clear_active_run(run_id)


async def execute_incremental_er_stage(
    run_id: str,
    input_dir: Path,
    *,
    candidate_top_k: int = 5,
    candidate_min_score: float = 0.85,
    enable_llm_blocking: bool = True,
):
    input_files = [path.name for path in sorted(input_dir.glob("*.json"))]

    try:
        _create_stage_run(
            run_id,
            "incremental_er_stage",
            input_files,
            {
                "stage": "incremental_er",
                "input_dir": str(input_dir),
                "artifacts_dir": str(ER_ARTIFACTS_DIR),
                "candidate_top_k": candidate_top_k,
                "candidate_min_score": candidate_min_score,
                "enable_llm_blocking": enable_llm_blocking,
            },
        )
        await _status(run_id, status="pending", progress=0, progress_pct=0, current_step=None, error_message=None)

        _update_run(run_id, status="resolving", current_step="incremental_er", progress_pct=0, error_message=None)
        await _status(
            run_id,
            status="resolving",
            progress=0,
            progress_pct=0,
            current_step="incremental_er",
            input_dir=str(input_dir),
            error_message=None,
        )

        async def on_er_progress(event: dict):
            if await _is_cancelled(run_id):
                return
            pct = int(event.get("progress_pct") or 0)
            pct = max(0, min(100, pct))
            step = event.get("step") or "incremental_er"
            message = event.get("message") or step
            _update_run(run_id, status="resolving", current_step=step, progress_pct=pct)
            _add_log(run_id, "info", message, step)
            await _status(
                run_id,
                status="resolving",
                progress=pct,
                progress_pct=pct,
                current_step=step,
                input_dir=str(input_dir),
                entity_resolution=event,
            )

        driver = get_neo4j_driver()
        vector_service = Neo4jVectorService(driver)
        result = await run_incremental_entity_resolution(
            input_dir=input_dir,
            neo4j_driver=driver,
            neo4j_vector_service=vector_service,
            run_id=run_id,
            artifacts_dir=ER_ARTIFACTS_DIR,
            progress_callback=on_er_progress,
            should_cancel=lambda: _is_cancelled_now(run_id),
            candidate_top_k=candidate_top_k,
            candidate_min_score=candidate_min_score,
            enable_llm_blocking=enable_llm_blocking,
        )
        if await _is_cancelled(run_id):
            return

        _update_run(run_id, status="completed", progress_pct=100, current_step=None)
        await _status(
            run_id,
            status="completed",
            progress=100,
            progress_pct=100,
            current_step=None,
            input_dir=str(input_dir),
            entity_resolution=result.to_dict(),
        )

    except asyncio.CancelledError:
        _update_run(run_id, status="failed", error_message="Cancelled by user")
        await _status(run_id, status="failed", error="Cancelled", error_message="Cancelled by user")
    except Exception as e:
        _update_run(run_id, status="failed", current_step="incremental_er", error_message=str(e))
        await _status(run_id, status="failed", error=str(e), error_message=str(e), current_step="incremental_er")
    finally:
        await _clear_active_run(run_id)


async def execute_pipeline(run_id: str, request: PipelineRunRequest):
    try:
        _create_run(run_id, request)
        await _status(run_id, status="pending", progress=0, progress_pct=0, current_step=None, error_message=None)

        input_dir = _selected_input_dir(run_id, request.files)
        mode = request.mode

        _update_run(run_id, status="extracting", current_step="extraction", progress_pct=10, error_message=None)
        await _status(run_id, status="extracting", progress=10, progress_pct=10, current_step="extraction", error_message=None)

        extraction_start_pct = 10
        extraction_end_pct = 60 if mode == "quick_import" else 30
        selected_files = sorted(input_dir.rglob("*.md"), key=lambda path: str(path.relative_to(input_dir)))

        async def on_extraction_progress(event: dict):
            if await _is_cancelled(run_id):
                return

            total = event.get("total") or 0
            processed = event.get("processed") or 0
            file_progress = (processed / total) if total else 1
            mapped_pct = extraction_start_pct + round((extraction_end_pct - extraction_start_pct) * file_progress)
            mapped_pct = max(extraction_start_pct, min(extraction_end_pct, mapped_pct))

            _update_run(run_id, status="extracting", current_step="extraction", progress_pct=mapped_pct)
            _add_log(
                run_id,
                "info",
                f"[{processed}/{total}] {event.get('status')}: {event.get('file')}",
                "extraction",
            )
            await _status(
                run_id,
                status="extracting",
                progress=mapped_pct,
                progress_pct=mapped_pct,
                current_step="extraction",
                file=event.get("file"),
                file_status=event.get("status"),
                extraction=event,
            )

        await run_extraction(
            input_dir=input_dir,
            output_dir=EXTRACTED_DIR,
            files=selected_files,
            run_id=run_id,
            progress_callback=on_extraction_progress,
            should_cancel=lambda: _is_cancelled_now(run_id),
            skip_existing=True,
            failed_dir=PROJECT_ROOT / "data" / "failed_responses",
        )
        if await _is_cancelled(run_id):
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
