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

# Run specific test files
python -m pytest services/entity_resolution/tests/test_llm_cer.py -v
python -m pytest services/entity_resolution/tests/test_e2e_mock_data.py -v

# Run with verbose output
python -m pytest services/entity_resolution/tests/ -v
```

### Knowledge Graph Extraction
```bash
# Extract KG from markdown files
python3 -m services.extraction.extract
```
Reads `*.md` from input directory, uses LLM to extract structured knowledge graphs into JSON files.

**Extraction Process:**
- Uses `KGExtractorV2` class with configurable LLM provider and model
- Generates JSON with `nodes` and `relationships` arrays
- Includes metadata: processing time, node/relation counts, model info, token usage
- Failed extractions saved to `data/failed_responses/` for debugging
- Supports retry logic (default: 3 attempts)

### Entity Resolution Pipeline
```bash
# Run full 3-stage pipeline (memory backend - fast, non-persistent)
python -m services.entity_resolution.cli \
  --stage all \
  --input-dir data/extracted \
  --store-backend memory \
  --run-id demo_run

# Run individual stages (qdrant backend - persistent)
python -m services.entity_resolution.cli \
  --stage stage1 \
  --input-dir data/extracted \
  --store-backend qdrant \
  --run-id my_run

python -m services.entity_resolution.cli \
  --stage stage2 \
  --store-backend qdrant \
  --run-id my_run

python -m services.entity_resolution.cli \
  --stage stage3 \
  --store-backend qdrant \
  --run-id my_run
```

**Key CLI Options:**
- `--llm-provider`: `proxypal` (default), `9router`, `openai`, `anthropic`
- `--llm-model`: Model name (default: `gpt-5` for proxypal, `cx/gpt-5.3-codex` for 9router)
- `--embedding-model`: Sentence transformer model (default: `paraphrase-multilingual-mpnet-base-v2`)
- `--cluster-threshold`: Cosine similarity threshold for clustering (default: 0.72)
- `--min-cluster-size`: Minimum entities per cluster (default: 2)
- `--cmr-threshold`: Merge threshold for canonical entity synthesis (default: 0.80)
- `--mdg-threshold`: MDG similarity threshold (default: 0.1)

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
- Dashboard saved to `artifacts/<run_id>/stage2/cluster_dashboard.html`

**Stage 3 - Resolution Pipeline (LLM-CER):**
- Uses LLM-based Collective Entity Resolution with three algorithms:
  - **NRS (Near-optimal Record Selection)**: Selects optimal record sets for LLM processing
  - **MDG (Merge Decision Generation)**: LLM generates merge decisions with validation
  - **CMR (Canonical Merged Record)**: Synthesizes canonical entities from clusters
- Outputs `id_remap.json` and rewrites graph files with merged entities
- Artifacts saved to `data/entity_resolution/artifacts/<run_id>/stage3/`

### LLM Integration (`services/llms/`)

Multi-provider abstraction layer with factory pattern:
- `get_llm(provider, **kwargs)` returns unified `BaseLLM` interface
- Supported providers: `proxypal`, `9router`, `gemini`, `ollama`
- All providers return response with `.content`, `.model`, `.usage_tokens`
- Registry-based client loading via `@register_llm` decorator

**Provider Details:**
- `proxypal`: OpenAI-compatible proxy (default base URL: `http://localhost:8317/v1`)
- `9router`: Router9 client for model routing
- `gemini`: Google Gemini API
- `ollama`: Local Ollama instance

Used in:
- Extraction pipeline (converts markdown to structured KG)
- Entity resolution stage 3 (LLM-CER: MDG and CMR algorithms)

## Key Configuration Files

- `.env` - LLM API keys, Neo4j credentials, Qdrant settings, model configuration
  - `PROXYPAL_KEY` and `PROXYPAL_BASE_URL` for Proxypal provider
  - `GOOGLE_API_KEY` for Gemini provider
  - `MODEL_LINK` and `PROVIDER_LINK` for entity resolution
  - `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` for Neo4j connection
  - `COLLECTION_NAME` for Qdrant collection
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

**Entity Resolution Output:**
- Stage 1: Vectors stored in Qdrant collection or memory
- Stage 2: Cluster assignments in `artifacts/<run_id>/stage2/clusters.json` and HTML dashboard
- Stage 3: `id_remap.json` (entity ID mappings) and rewritten graph files in `artifacts/<run_id>/stage3/output/`

**LLM-CER Algorithm Parameters:**
- `llm_set_size`: Optimal record set size for NRS (default: 9)
- `mdg_similarity_threshold`: Threshold for MDG validation (default: 0.15)
- `cmr_merge_threshold`: Similarity threshold for CMR merging (default: 0.80)
- `conservative_merge_threshold`: High threshold for conservative fallback (default: 0.88)

**Neo4j Import:**
- Import script uses MERGE on node `id` (unique constraint)
- Labels are sanitized (removes special characters, prefixes digits with `L_`)
- All nodes get `:KgNode` base label plus their specific labels
- Relationships use sanitized type names

**Frontend Build:**
- `npm run build` creates production build in `dist/`
- `npm run preview` previews production build locally
- Docker uses multi-stage build: Node 22 Alpine (build) → Nginx Alpine (serve)
