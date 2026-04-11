# AGENTS.md

## Use these commands (repo-root unless noted)
- Start local infra: `docker compose up -d` (Ollama `11434`, Neo4j `7474/7687`, Qdrant `6333`).
- Backend dev server: `uvicorn apps.backend.app.main:app --host 0.0.0.0 --port 8000 --reload`.
- Frontend dev server: `cd apps/frontend && npm install && npm run dev`.
- Extraction: `python3 -m services.extraction.extract` (default output is `data/extracted`).
- Import extracted graph to Neo4j: `python apps/backend/neo4j/scripts/import_to_neo4j.py --dir data/extracted`.
- Entity resolution full run (memory backend): `python -m services.entity_resolution.cli --stage all --input-dir data/extracted --store-backend memory --run-id <run_id>`.

## Test commands that are currently reliable
- This repo is being run with conda env `py312`; use `conda run -n py312 ...` for reproducible test runs.
- Entity resolution suite: `conda run -n py312 python -m pytest services/entity_resolution/tests -q`.
- Frontend lint: `cd apps/frontend && npm run lint`.
- Frontend build: `cd apps/frontend && npm run build`.

## Known breakages / gotchas
- `services/extraction/README.md` is stale (mentions old `extractv2` layout); use `services/extraction/extract.py` as source of truth.
- Entity resolution code is under `services/entity_resolution/pipelines/*_pipeline.py` (not `stage1/`, `stage2/`, `stage3/` packages).
- With `--store-backend memory`, you must run `--stage all` in one process; data is not persisted across separate CLI invocations.
- Entity resolution artifacts are written to `entity_resolution/artifacts/<run_id>/stage1|stage2|stage3`.

## Import-path conventions
- Keep Python commands at repo root so `services.*` imports resolve consistently.
- Frontend API base URL is read from `apps/frontend/.env.development` (`VITE_API_BASE_URL`, default `http://localhost:8000`).

## Repo instruction sources
- Main agent guidance is in `CLAUDE.md`; prefer code/config if docs conflict.
- `.gitignore` ignores `*.md`; `!AGENTS.md` is explicitly allowed so this file can be tracked.
