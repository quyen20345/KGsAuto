import asyncio
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from apps.pipeline_api import runner
from apps.pipeline_api.main import app
from apps.pipeline_api.routes import files as files_route


@pytest.fixture(autouse=True)
def reset_runner_state():
    runner._active_process = None
    runner._active_run_id = None
    runner._cancelling_run_id = None
    yield
    runner._active_process = None
    runner._active_run_id = None
    runner._cancelling_run_id = None


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("apps.pipeline_api.main.validate_settings", lambda service: None)
    return TestClient(app)


def test_upload_rejects_traversal_filename(client, tmp_path, monkeypatch):
    monkeypatch.setattr(files_route, "RAW_DIR", tmp_path)
    monkeypatch.setattr("apps.pipeline_api.paths.RAW_DIR", tmp_path)

    response = client.post(
        "/api/files/upload",
        files=[("files", ("../evil.md", b"bad", "text/markdown")), ("files", ("ok.md", b"ok", "text/markdown"))],
    )

    assert response.status_code == 200
    assert response.json() == {"uploaded": ["ok.md"], "skipped": ["../evil.md"]}
    assert (tmp_path / "ok.md").read_bytes() == b"ok"
    assert not (tmp_path.parent / "evil.md").exists()


def test_delete_rejects_traversal_filename(client, tmp_path, monkeypatch):
    monkeypatch.setattr(files_route, "RAW_DIR", tmp_path)
    monkeypatch.setattr("apps.pipeline_api.paths.RAW_DIR", tmp_path)
    (tmp_path / "ok.md").write_text("ok", encoding="utf-8")

    response = client.delete("/api/files/raw/..%2Fevil.md")

    assert response.status_code == 404
    assert (tmp_path / "ok.md").exists()


def test_reserve_run_is_atomic():
    async def run():
        return await asyncio.gather(runner.reserve_run("a"), runner.reserve_run("b"))

    results = asyncio.run(run())

    assert results.count(True) == 1
    assert results.count(False) == 1


def test_selected_input_dir_copies_only_selected_files(tmp_path, monkeypatch):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "a.md").write_text("a", encoding="utf-8")
    (raw_dir / "b.md").write_text("b", encoding="utf-8")
    project_root = tmp_path / "project"

    monkeypatch.setattr("apps.pipeline_api.paths.RAW_DIR", raw_dir)
    monkeypatch.setattr(runner, "RAW_DIR", raw_dir)
    monkeypatch.setattr(runner, "PROJECT_ROOT", project_root)

    input_dir = runner._selected_input_dir("run1", ["a.md"])

    assert sorted(p.name for p in input_dir.glob("*.md")) == ["a.md"]
    assert (input_dir / "a.md").read_text(encoding="utf-8") == "a"


def test_cancel_run_marks_failed_and_waits(monkeypatch):
    proc = SimpleNamespace(pid=1234, returncode=None)
    waited = False

    async def wait():
        nonlocal waited
        waited = True
        proc.returncode = -15

    proc.wait = wait
    runner._active_run_id = "run1"
    runner._active_process = proc
    updates = []
    broadcasts = []

    monkeypatch.setattr(runner.os, "killpg", lambda pid, sig: None)
    monkeypatch.setattr(runner, "_update_run", lambda run_id, **kwargs: updates.append((run_id, kwargs)))
    async def broadcast(run_id, event):
        broadcasts.append((run_id, event))

    monkeypatch.setattr(runner, "_broadcast", broadcast)

    assert asyncio.run(runner.cancel_run("run1")) is True
    assert waited is True
    assert updates[-1][1]["status"] == "failed"
    assert broadcasts[-1][1]["error_message"] == "Cancelled by user"


def test_execute_pipeline_uses_in_process_extraction_for_quick_import(tmp_path, monkeypatch):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "a.md").write_text("a", encoding="utf-8")

    request = runner.PipelineRunRequest(mode="quick_import")
    runner._active_run_id = "run1"
    updates = []
    statuses = []
    logs = []
    subprocess_calls = []
    extraction_call = {}

    monkeypatch.setattr(runner, "_create_run", lambda run_id, request: None)
    monkeypatch.setattr(runner, "_selected_input_dir", lambda run_id, files: input_dir)
    monkeypatch.setattr(runner, "_update_run", lambda run_id, **kwargs: updates.append((run_id, kwargs)))
    monkeypatch.setattr(runner, "_add_log", lambda run_id, level, message, step=None: logs.append((run_id, level, message, step)))

    async def status(run_id, **event):
        statuses.append((run_id, event))

    async def fake_run_extraction(**kwargs):
        extraction_call.update(kwargs)
        assert kwargs["should_cancel"]() is False
        await kwargs["progress_callback"]({
            "file": "a.md",
            "status": "completed",
            "processed": 1,
            "total": 1,
            "successful": 1,
            "failed": 0,
            "skipped": 0,
            "progress_pct": 100,
        })

    async def fake_run_subprocess(run_id, step, args):
        subprocess_calls.append((step, args))
        return 0

    monkeypatch.setattr(runner, "_status", status)
    monkeypatch.setattr(runner, "run_extraction", fake_run_extraction)
    monkeypatch.setattr(runner, "_run_subprocess", fake_run_subprocess)

    asyncio.run(runner.execute_pipeline("run1", request))

    assert [path.name for path in extraction_call["files"]] == ["a.md"]
    assert subprocess_calls == [("neo4j_import", ["-m", "services.neo4j_import.import_to_neo4j", "--dir", str(runner.EXTRACTED_DIR)])]
    assert not any("services.extraction.cli" in arg for _, args in subprocess_calls for arg in args)
    assert any(event.get("file") == "a.md" and event.get("progress_pct") == 60 for _, event in statuses)
    assert updates[-1][1]["status"] == "completed"

