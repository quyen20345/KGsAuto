import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from apps.pipeline_api.config import RAW_DIR, EXTRACTED_DIR, ER_ARTIFACTS_DIR
from apps.pipeline_api.models import (
    ERRunInfo,
    ExtractedFileInfo,
    FileInfo,
    UploadResponse,
)
from apps.pipeline_api.paths import safe_raw_markdown_path

router = APIRouter(prefix="/api/files", tags=["files"])


def _file_info(path: Path, check_extraction: bool = False) -> FileInfo:
    stat = path.stat()
    has_extraction = False
    if check_extraction:
        kg_name = path.stem + "_kg.json"
        has_extraction = (EXTRACTED_DIR / kg_name).exists()
    return FileInfo(
        name=path.name,
        size=stat.st_size,
        modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        has_extraction=has_extraction,
    )


def _extracted_file_info(path: Path) -> ExtractedFileInfo:
    stat = path.stat()
    node_count = None
    rel_count = None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        nodes = data.get("nodes")
        rels = data.get("relationships")
        if isinstance(nodes, list):
            node_count = len(nodes)
        if isinstance(rels, list):
            rel_count = len(rels)
    except Exception:
        pass
    return ExtractedFileInfo(
        name=path.name,
        size=stat.st_size,
        modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        node_count=node_count,
        rel_count=rel_count,
    )


@router.get("/raw")
async def list_raw_files() -> list[FileInfo]:
    if not RAW_DIR.exists():
        return []
    files = sorted(RAW_DIR.glob("*.md"), key=lambda p: p.name)
    return [_file_info(f, check_extraction=True) for f in files]


@router.get("/extracted")
async def list_extracted_files() -> list[ExtractedFileInfo]:
    if not EXTRACTED_DIR.exists():
        return []
    files = sorted(EXTRACTED_DIR.glob("*_kg.json"), key=lambda p: p.name)
    return [_extracted_file_info(f) for f in files]


@router.get("/resolved")
async def list_resolved_runs() -> list[ERRunInfo]:
    if not ER_ARTIFACTS_DIR.exists():
        return []
    runs = []
    for run_dir in sorted(ER_ARTIFACTS_DIR.iterdir()):
        if not run_dir.is_dir():
            continue
        output_count = 0
        stage3_output = run_dir / "stage3" / "output_graph"
        if stage3_output.exists():
            output_count = len(list(stage3_output.glob("*.json")))
        runs.append(ERRunInfo(
            run_id=run_dir.name,
            has_stage1=(run_dir / "stage1").exists(),
            has_stage2=(run_dir / "stage2").exists(),
            has_stage3=(run_dir / "stage3").exists(),
            output_file_count=output_count,
        ))
    return runs


@router.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)) -> UploadResponse:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    uploaded = []
    skipped = []
    for f in files:
        try:
            dest = safe_raw_markdown_path(f.filename or "")
        except HTTPException:
            skipped.append(f.filename or "unknown")
            continue
        if dest.exists():
            skipped.append(f.filename)
            continue
        content = await f.read()
        dest.write_bytes(content)
        uploaded.append(f.filename)
    return UploadResponse(uploaded=uploaded, skipped=skipped)


@router.delete("/raw/{filename}")
async def delete_raw_file(filename: str):
    path = safe_raw_markdown_path(filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    path.unlink()
    return {"deleted": filename}
