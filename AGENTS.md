# AGENTS.md

## Use These Commands
- Repo-root unless noted.
- Start local infra: `docker compose up -d` (Ollama `11434`, Neo4j `7474/7687`, Qdrant `6333`).
- Backend dev server: `uvicorn apps.backend.app.main:app --host 0.0.0.0 --port 8000 --reload`.
- Frontend dev server: `cd apps/frontend && npm run dev`.
- Extraction: `python3 -m services.extraction.extract`.
- Import extracted graph to Neo4j: `python apps/backend/neo4j/scripts/import_to_neo4j.py --dir data/extracted`.
- Entity resolution full run with memory store: `python -m services.entity_resolution.cli --stage all --input-dir data/extracted --store-backend memory --run-id <run_id>`.

## Fast Verification
- Use `conda run -n py312 ...` for reproducible Python test runs.
- Backend tests: `conda run -n py312 python -m pytest apps/backend/tests -q`.
- Single backend test file: `conda run -n py312 python -m pytest apps/backend/tests/<file>.py -q`.
- Entity resolution suite: `conda run -n py312 python -m pytest services/entity_resolution/tests -q`.
- Focused ER test: `conda run -n py312 python -m pytest services/entity_resolution/tests/test_llm_cer.py -v`.
- Frontend lint: `cd apps/frontend && npm run lint`.
- Frontend build: `cd apps/frontend && npm run build`.

## Repo Boundaries
- `apps/backend`: FastAPI app. Real entrypoint is `apps.backend.app.main:app`.
- `apps/frontend`: Vite + React app. API client is `apps/frontend/src/services/api.js`.
- `services/extraction`: Markdown -> KG JSON extraction. Source of truth is `services/extraction/extract.py`.
- `services/entity_resolution`: 3-stage pipeline orchestrated by `services/entity_resolution/pipelines/stage1_pipeline.py`, `stage2_pipeline.py`, and `stage3_pipeline.py`.
- `services/llms`: Shared LLM provider abstraction used by extraction and entity resolution.

## Gotchas
- `services/extraction/README.md` is stale (mentions old `extractv2` layout); use `services/extraction/extract.py` as source of truth.
- Entity resolution code is under `services/entity_resolution/pipelines/*_pipeline.py` (not `stage1/`, `stage2/`, `stage3/` packages).
- With `--store-backend memory`, you must run `--stage all` in one process; data is not persisted across separate CLI invocations.
- Entity resolution CLI defaults come from `services/entity_resolution/cli.py`; default artifacts root is `entity_resolution/artifacts/<run_id>/...`.
- `services/entity_resolution/README.md` has stale artifact paths in places; trust `cli.py` over the README.
- Extraction defaults in code are input `data/raw/uet` and output `data/extracted`.

## Conventions
- Keep Python commands at repo root so `services.*` imports resolve consistently.
- Frontend API base URL is `VITE_API_BASE_URL`; code falls back to `http://localhost:8000` if unset.
- Frontend requests are under `/api/...` in `apps/frontend/src/services/api.js`, so backend changes should preserve that prefix unless frontend is updated too.

## Instruction Sources
- Main agent guidance is in `CLAUDE.md`.
- Prefer executable sources over prose when docs conflict: `services/entity_resolution/cli.py`, `services/extraction/extract.py`, `apps/frontend/src/services/api.js`, `apps/frontend/package.json`.
- `.gitignore` ignores `*.md`; `!AGENTS.md` is explicitly allowed so this file can be tracked.
