# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

KGsAuto is a Knowledge Graph Automation System that extracts, links, and visualizes knowledge graphs from markdown documents using LLMs and graph databases.

**Tech Stack:**
- Backend: FastAPI + Neo4j (graph database) + Qdrant (vector database)
- Frontend: React 19 + Vite 8 + React Router
- LLM Integration: Multi-provider abstraction (Proxypal/OpenAI-compatible, Google Gemini, Ollama)
- Python 3.10+

## Common Development Commands

### Start Infrastructure Services
```bash
docker compose up -d
```
This starts Ollama (port 11434), Neo4j (ports 7474, 7687), and Qdrant (port 6333).

### Backend Development
```bash
# From repo root
uvicorn apps.backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
Access at: http://localhost:8000/docs (Swagger UI)

### Frontend Development
```bash
cd apps/frontend && npm run dev
```
Access at: http://localhost:5173

### Run Tests
```bash
# Backend tests
python -m pytest apps/backend/tests -q

# Entity resolution tests (from repo root)
python -m pytest services/entity_resolution/tests/ -q

# Run specific stage tests
python -m pytest services/entity_resolution/tests/stage1 -q
python -m pytest services/entity_resolution/tests/stage2 -q
python -m pytest services/entity_resolution/tests/stage3 -q
```

### Knowledge Graph Extraction
```bash
# Extract KG from markdown files
python3 -m services.extraction.extract
```
Reads `*.md` from input directory, uses LLM to extract structured knowledge graphs into JSON files.

### Entity Resolution Pipeline
```bash
# Run full 3-stage pipeline
python -m services.entity_resolution.cli \
  --stage all \
  --input-dir data/extracted \
  --store-backend memory \
  --run-id demo_run \
  --review-mode human_required

# Run individual stages (requires qdrant backend)
python -m services.entity_resolution.cli --stage stage1 --input-dir data/extracted --store-backend qdrant --run-id my_run
python -m services.entity_resolution.cli --stage stage2 --store-backend qdrant --run-id my_run
python -m services.entity_resolution.cli --stage stage3 --store-backend qdrant --run-id my_run --review-mode human_required
```

**Important:** When using `--store-backend memory`, you must run `--stage all` in a single command. Memory backend does not persist between separate CLI invocations. Use `qdrant` backend to run stages separately.

### Import Knowledge Graph to Neo4j
```bash
python apps/backend/neo4j/scripts/import_to_neo4j.py --dir data/extracted
```

## Architecture

### Repository Structure

```
KGsAuto/
├── apps/                 # Deployable applications
│   ├── backend/          # FastAPI application
│   └── frontend/         # React application
├── services/             # Reusable Python services
│   ├── extraction/       # KG extraction service
│   ├── entity_resolution/ # Entity deduplication pipeline
│   └── llms/             # LLM abstraction layer
├── data/                 # Data files (extracted, raw, mock)
├── scripts/              # Utility scripts
├── .claude/              # Claude Code configuration
├── CLAUDE.md             # Project documentation
├── README.md             # Quick start guide
├── docker-compose.yml    # Infrastructure services
├── pyproject.toml        # Python project configuration
└── .env.example          # Environment variables template
```

### Data Flow Pipeline

1. **Extraction** (`services/extraction/`): Markdown → LLM → JSON knowledge graphs
2. **Entity Resolution** (`services/entity_resolution/`): 3-stage deduplication pipeline
   - Stage 1: Embedding & vectorization (stores in Qdrant)
   - Stage 2: Clustering similar entities (HDBSCAN or cosine threshold)
   - Stage 3: Human-in-the-loop review + canonical entity synthesis
3. **Import**: Load resolved JSON graphs into Neo4j
4. **Backend API** (`apps/backend/`): FastAPI service for querying Neo4j
5. **Frontend UI** (`apps/frontend/`): React app for browsing and visualizing the graph

### Backend Structure (`apps/backend/`)

FastAPI application with modular routers:
- `routers/health.py` - Health check endpoint
- `routers/entity.py` - Entity search and detail (`/api/search`, `/api/entity/{id}`)
- `routers/graph.py` - Graph queries, random triplets, visualization, metadata

**Database Integration:**
- Neo4j: Singleton driver pattern in `app/db/neo4j.py`, lazy initialization
- Qdrant: Used by entity linking services for semantic similarity search

**Key Design Patterns:**
- Service layer pattern (business logic separated from routers)
- Dependency injection for testability
- Pydantic schemas for request/response validation

### Frontend Structure (`apps/frontend/`)

React SPA with client-side routing:
- `pages/Home.jsx` - Displays random triplets from the graph
- `pages/Search.jsx` - Entity search results
- `pages/Entity.jsx` - Entity detail view with properties and relationships
- `services/api.js` - Backend API client (reads `VITE_API_BASE_URL` from env)

**Environment Configuration:**
- `.env.development` sets `VITE_API_BASE_URL=http://localhost:8000`
- Vite automatically loads `VITE_*` prefixed variables

### Entity Resolution (`services/entity_resolution/`)

3-stage pipeline for entity deduplication:

**Stage 1 - Embedding Pipeline:**
- Loads JSON graph files, normalizes node properties
- Creates `embedding_text` representation for each entity
- Generates vectors (semantic embeddings or hash-based)
- Stores in Qdrant or memory backend

**Stage 2 - Clustering Pipeline:**
- Fetches vectors from storage
- Clusters by `primary_type` using HDBSCAN or cosine threshold
- Outputs cluster assignments and HTML dashboard for visualization

**Stage 3 - Resolution Pipeline (2-pass):**
- Pass 1: Cluster validation (MERGE/SKIP/SPLIT decisions)
- Pass 2: Canonical entity synthesis (LLM suggests merged entity, human approves)
- Generates `id_remap.json` and rewrites graph files with merged entities

**Human Review Workflow:**
1. Run stage3 with `--review-mode human_required`
2. Open `artifacts/<run_id>/stage3/review_dashboard.html`
3. Copy `human_cluster_decisions.template.json` → `human_cluster_decisions.json`, edit decisions
4. Re-run stage3 (same run_id) to generate synthesis proposals
5. Copy `human_synthesis_decisions.template.json` → `human_synthesis_decisions.json`, approve proposals
6. Re-run stage3 to apply merges and rewrite output files

### LLM Integration (`services/llms/`)

Multi-provider abstraction layer:
- `get_llm(provider, model_name)` returns unified interface
- Supported providers: `proxypal` (OpenAI-compatible), `gemini`, `ollama`
- All providers return response with `.content`, `.model`, `.usage_tokens`

Used in:
- Extraction pipeline (converts markdown to structured KG)
- Entity resolution stage 3 (cluster hints and canonical entity synthesis)

## Key Configuration Files

- `.env` - LLM API keys, Neo4j credentials, Qdrant settings
- `docker-compose.yaml` - Infrastructure services (Ollama, Neo4j, Qdrant)
- `pyproject.toml` - Python project configuration and dependencies
- `apps/backend/requirements.txt` - Backend-specific dependencies
- `apps/frontend/package.json` - Frontend dependencies and scripts

## Service Access Points

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000/docs
- Neo4j Browser: http://localhost:7474 (neo4j / 12345678)
- Qdrant Dashboard: http://localhost:6333/dashboard
- Ollama: http://localhost:11434

## Important Notes

**Running from Repo Root:**
- Always run backend and entity resolution commands from the repository root
- Use: `uvicorn apps.backend.app.main:app ...` not `cd apps/backend && uvicorn app.main:app ...`

**Entity Resolution Storage Backends:**
- `memory`: Fast for testing, but data lost between CLI invocations. Use `--stage all` in one command.
- `qdrant`: Persistent storage, allows running stages separately across multiple CLI invocations.

**Neo4j Import:**
- Import script uses MERGE on node `id` (unique constraint)
- Labels are sanitized (removes special characters, prefixes digits with `L_`)
- All nodes get `:KgNode` base label plus their specific labels
- Relationships use sanitized type names

**Frontend Build:**
- `npm run build` creates production build in `dist/`
- `npm run preview` previews production build locally
- Docker uses multi-stage build: Node 22 Alpine (build) → Nginx Alpine (serve)
