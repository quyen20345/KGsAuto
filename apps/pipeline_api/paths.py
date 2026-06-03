from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException

from apps.pipeline_api.config import PROJECT_ROOT, RAW_DIR


def safe_raw_markdown_path(filename: str) -> Path:
    if not filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    path = Path(filename)
    if path.name != filename or filename in {".", ".."} or path.suffix != ".md":
        raise HTTPException(status_code=400, detail="Invalid filename")

    raw_root = RAW_DIR.resolve()
    candidate = (RAW_DIR / filename).resolve(strict=False)
    if candidate.parent != raw_root:
        raise HTTPException(status_code=400, detail="Invalid filename")

    if candidate.exists() and not candidate.is_relative_to(raw_root):
        raise HTTPException(status_code=400, detail="Invalid filename")

    return candidate


def safe_project_dir_path(
    value: str,
    *,
    create: bool = False,
    must_exist: bool = False,
) -> Path:
    if not value or not value.strip():
        raise HTTPException(status_code=400, detail="Directory path is required")

    raw = Path(value.strip())
    if any(part == ".." for part in raw.parts):
        raise HTTPException(status_code=400, detail="Directory path must not contain '..'")

    project_root = PROJECT_ROOT.resolve()
    candidate = raw.resolve(strict=False) if raw.is_absolute() else (project_root / raw).resolve(strict=False)
    if not candidate.is_relative_to(project_root):
        raise HTTPException(status_code=400, detail="Directory path must stay inside the project workspace")

    if must_exist and (not candidate.exists() or not candidate.is_dir()):
        raise HTTPException(status_code=404, detail=f"Directory not found: {value}")

    if create:
        candidate.mkdir(parents=True, exist_ok=True)
    elif candidate.exists() and not candidate.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {value}")

    return candidate

