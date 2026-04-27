# Repository Guidelines

## Project Structure & Module Organization
KGsAuto is a Python/React knowledge-graph system. FastAPI apps live in `apps/`: `apps/backend` is the main graph API and `apps/rag_api` is the unified retrieval/RAG API. Core packages are in `services/`, including `entity_resolution`, `rag_system`, `llms`, and `crawler`. Unified RAG code lives in `services/rag_system`: `core/` orchestrates modes, `retrieval/` handles Qdrant/Neo4j retrieval, `graph_search/` contains Neo4j-only GraphSearch reasoning, `storage/` wraps stores, and `evaluation/` contains scoring utilities. The Vite UI is in `apps/frontend/src`, with components in `components/` and route pages in `pages/`. Generated or local artifacts should stay under `data/`.

## Build, Test, and Development Commands
- `docker compose up -d`: start local Neo4j, Qdrant, and Ollama infrastructure.
- `uvicorn apps.backend.app.main:app --host 0.0.0.0 --port 8000 --reload`: run the main backend API.
- `uvicorn apps.rag_api.main:app --host 0.0.0.0 --port 8001 --reload`: run the unified RAG API with `semantic_search`, `graph_search`, `naive_grag`, and `hybrid` modes.
- `python -m services.rag_system.cli query --question "Hiệu trưởng là ai?" --mode semantic_search --top-k 5 --show-evidence`: run a local CLI query.
- `cd apps/frontend && npm install && npm run dev`: install frontend dependencies and start Vite.
- `cd apps/frontend && npm run build`: build the frontend for production.
- `cd apps/frontend && npm run lint`: run ESLint.
- `conda run -n py312 python -m pytest services/rag_system/tests apps/rag_api/tests -q`: run unified RAG/API tests.

## Coding Style & Naming Conventions
Use Python 3.10+ with 4-space indentation, `snake_case` modules/functions, and `PascalCase` classes and Pydantic models. Keep API routers thin and reusable logic in `services/`. For React, use `PascalCase` component files such as `EntityPopover.jsx`, keep route views in `pages/`, and keep API calls in `src/services/api.js`. Frontend linting uses ESLint; no central Python formatter is configured, so keep Python changes PEP 8 compatible.

## Testing Guidelines
Use `pytest` for Python tests. Prefer colocated test packages such as `apps/backend/tests`, `apps/rag_api/tests`, or `services/rag_system/tests`. Name files `test_*.py` and cover changed pipeline stages, API routes, and storage adapters. For frontend changes, run `npm run lint`.

## Commit & Pull Request Guidelines
Recent history uses short imperative subjects, often with scopes, for example `feat(entity_resolution): ...` and `feat(frontend): ...`. Prefer focused commits that name the affected area. Pull requests should include a summary, test results, linked issue or task when available, and screenshots for UI changes. Note required `.env` values, data migrations, or Neo4j/Qdrant setup.

## Security & Configuration Tips
Do not commit secrets. Copy `.env.example` files for local setup and keep provider keys, Neo4j credentials, and model routing values in `.env`. Commit only reproducible fixtures or reviewed sample data.
