from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException

from apps.pipeline_api.config import RAW_DIR


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
