# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

**KGsAuto** is a Vietnamese Knowledge Graph automation system for a thesis project. It extracts entities and relationships from unstructured markdown text, performs intelligent entity linking to resolve duplicates, and stores the cleaned data in a Neo4j graph database with vector search capabilities.

**Core Purpose:** Automate knowledge graph construction from Vietnamese academic documents (VNU data) using LLM-based extraction and sophisticated entity resolution.

---

## High-Level Architecture

KGsAuto follows a classic **ETL (Extract-Transform-Load) pipeline** with three main stages:

```
┌─────────────────────────────────────────────────────────────┐
│ STAGE 1: EXTRACT                                            │
│ (extract/ module)                                           │
│ - Read markdown files from data/raw/uet/                   │
│ - Use LLM to extract entities & relationships              │
│ - Output: JSON files with nodes/relationships              │
│ - Location: data/extracted/*_kg.json                       │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ STAGE 2: ENTITY LINKING (Transform)                         │
│ (entity_linking/ module)                                    │
│ - Load all extracted KG files                              │
│ - Upsert entities into Qdrant (vector embeddings)          │
│ - Iterative similarity search + LLM-based merge decisions  │
│ - Rewrite JSON with canonical entity IDs                   │
│ - Location: data/import_linked/*_kg.json                   │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ STAGE 3: IMPORT TO NEO4J (Load)                             │
│ (neo4j/scripts/ module)                                     │
│ - Batch import nodes and relationships                      │
│ - Create constraints and indexes                            │
│ - Result: Queryable graph in Neo4j                          │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ STAGE 4: QUERY & VISUALIZATION                              │
│ (backend/ + frontend/ modules)                              │
│ - FastAPI backend exposes Cypher query endpoints            │
│ - React frontend displays graph visualization               │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Purpose | Technology |
|-----------|---------|-----------|
| **extract/** | LLM-based entity extraction | Python, LLM providers |
| **entity_linking/** | Duplicate resolution via vector similarity + LLM | Qdrant, SentenceTransformers |
| **backend/** | REST API for graph queries | FastAPI, Neo4j driver |
| **frontend/** | Web UI for visualization | React 19, Vite, React Router |
| **llms/** | Multi-provider LLM abstraction | Factory pattern, Gemini/ProxyPal/Ollama |
| **neo4j/** | Import scripts and utilities | Neo4j Python driver |

### Data Flow

```
Raw Markdown (data/raw/uet/*.md)
    ↓ [LLM Extraction]
Extracted KG JSON (data/extracted/*_kg.json)
    ↓ [Vector Embeddings + LLM Merging]
Linked KG JSON (data/import_linked/*_kg.json)
    ↓ [Batch Import]
Neo4j Graph Database
    ↓ [REST API]
Frontend Visualization
```

---

## Common Commands

### Setup

```bash
# Copy environment configuration
cp .env.example .env

# Start Docker services (Neo4j, Qdrant, Ollama)
docker compose up -d

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install
```

### Run the Full Pipeline

```bash
# Interactive mode (choose steps)
./run.sh

# Or run specific steps:
./run.sh extract    # Extract entities from markdown
./run.sh link       # Resolve duplicate entities
./run.sh import     # Import to Neo4j
./run.sh run        # Run full pipeline (extract → link → import)
```

### Run Individual Modules

```bash
# Extract entities
python -m extract.extractor --dir data/raw/uet --out data/extracted

# Entity linking
python -m entity_linking.cli

# Import to Neo4j
python neo4j/scripts/import_to_neo4j.py --dir data/import_linked
```

### Backend Development

```bash
# Start FastAPI dev server (port 8000)
uvicorn backend.app.main:app --port 8000 --reload

# Access API docs: http://localhost:8000/docs
```

### Frontend Development

```bash
cd frontend

# Start Vite dev server (port 5173)
npm run dev

# Build for production
npm run build

# Lint code
npm run lint

# Preview production build
npm run preview
```

### Service Access

```bash
# Neo4j Browser (query graph directly)
http://localhost:7474
# Credentials: neo4j / 12345678

# Qdrant Dashboard (vector store UI)
http://localhost:6333/dashboard

# Ollama API (local LLM)
http://localhost:11434

# Backend API
http://localhost:8000

# Frontend
http://localhost:5173
```

---

## Key Architectural Patterns

### 1. LLM Factory Pattern (llms/factory.py)

The system uses a **registry-based factory** for pluggable LLM providers:

```python
@register_llm("gemini")
class GeminiClient(BaseLLM):
    def generate(self, prompt: str) -> str: ...

@register_llm("ollama")
class OllamaClient(BaseLLM):
    def generate(self, prompt: str) -> str: ...
```

**Key insight:** All LLM calls go through a unified `BaseLLM` interface. To add a new provider, register a new client class with the decorator.

### 2. Entity Linking Algorithm (entity_linking/linker.py)

The entity linking uses a **two-phase approach**:

**Phase 1: Vector Similarity Search**
- Embed all entities using SentenceTransformer (`all-MiniLM-L6-v2`)
- Store in Qdrant vector database
- For each entity, find similar candidates using cosine similarity
- Filter by score threshold (default: 0.85)

**Phase 2: LLM-Based Decision**
- For each candidate pair, ask LLM: "Should these entities be merged?"
- LLM returns structured JSON with merge decision
- If merge approved: combine entities, update canonical ID, delete duplicate
- Track merge history in `merged_ids` field for audit trail

**Concurrency:** Uses ThreadPoolExecutor to parallelize LLM calls (8 workers default)

**Convergence:** Runs multiple iterations until no more merges occur (max 5 iterations)

### 3. Canonical ID Strategy

When two entities merge:
- **Seed entity ID** (the one being searched) becomes the canonical ID
- **Candidate entity ID** is absorbed into seed
- All relationships are remapped to canonical ID
- Merge history tracked in `merged_ids` array

**Benefit:** Maintains audit trail and prevents circular merges

### 4. Schema-First Extraction (extract/extractor.py)

Entity extraction uses **strict schema constraints**:
- 10 predefined entity types (PERSON, ORGANIZATION, PUBLICATION, etc.)
- Predefined relationship types
- LLM is instructed to only extract within schema
- Prevents hallucination and ensures data consistency

### 5. Concurrent Processing

Multiple optimizations for large datasets:
- **Batch scrolling:** Load entities in batches (256 per batch) to avoid N+1 queries
- **Pair deduplication:** Track attempted pairs to avoid redundant LLM calls
- **ThreadPoolExecutor:** Parallelize LLM calls across multiple threads
- **Idempotent imports:** Neo4j MERGE operations allow re-running imports safely

---

## Configuration

### Environment Variables (.env)

```bash
# LLM API Keys
GOOGLE_API_KEY=your-google-api-key-here
PROXYPAL_KEY=proxypal-local

# Model Configuration
DEFAULT_MODEL=gemini-2.5-flash
DEFAULT_TEMPERATURE=0.7

# Neo4j Database
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=12345678

# Entity Linking (optional - defaults shown)
EL_KG_DIR=data/extracted
EL_OUTPUT_DIR=data/import_linked
EL_SCORE_THRESHOLD=0.85          # Vector similarity threshold
EL_MAX_WORKERS=8                 # Concurrent LLM calls
EL_MAX_ITERATIONS=10             # Max linking iterations
EL_LIMIT=10                      # Max candidates per entity
EL_LOG_LEVEL=INFO
```

### Data Directories

```
data/
├── raw/uet/              # Input markdown files
├── extracted/            # Output from extraction stage
└── import_linked/        # Output from entity linking stage
```

---

## Development Workflow

### Adding a New LLM Provider

1. Create client class in `llms/clients/`
2. Inherit from `BaseLLM`
3. Implement `generate()` method
4. Register with `@register_llm("provider_name")` decorator
5. Add API key to `.env`

### Modifying Entity Extraction

1. Edit extraction prompt in `extract/extractor.py`
2. Update entity schema if adding new types
3. Test with sample markdown files
4. Run: `python -m extract.extractor`

### Tuning Entity Linking

1. Adjust `EL_SCORE_THRESHOLD` to change similarity sensitivity
2. Modify LLM prompt in `entity_linking/linker.py` (lines 15-83)
3. Increase `EL_MAX_WORKERS` for faster processing (if API allows)
4. Run: `python -m entity_linking.cli`

### Adding Backend API Endpoints

1. Create router in `backend/app/routers/`
2. Use APIRouter with prefix and tags
3. Use Pydantic models for request/response
4. Inject Neo4j driver via dependency injection
5. Register router in `backend/app/main.py`

### Adding Frontend Pages

1. Create component in `frontend/src/pages/`
2. Add route in `frontend/src/App.jsx`
3. Use React Router hooks (`useNavigate`, `useParams`)
4. Call backend API via `frontend/src/services/api.js`

---

## Important Files & Their Roles

| File | Purpose |
|------|---------|
| `run.sh` | Main pipeline orchestrator (interactive or CLI) |
| `extract/extractor.py` | LLM-based entity extraction logic |
| `entity_linking/linker.py` | Entity linking algorithm with LLM decisions |
| `entity_linking/entity_store.py` | Qdrant vector store wrapper |
| `entity_linking/pipeline.py` | End-to-end entity linking orchestration |
| `backend/app/main.py` | FastAPI app initialization |
| `backend/app/routers/` | API endpoint definitions |
| `backend/app/db/neo4j.py` | Neo4j driver management |
| `frontend/src/App.jsx` | React app with routes |
| `frontend/src/services/api.js` | Backend API client |
| `llms/factory.py` | LLM provider registry and factory |
| `neo4j/scripts/import_to_neo4j.py` | Batch import script |
| `docker-compose.yaml` | Service definitions (Neo4j, Qdrant, Ollama) |

---

## Debugging Tips

### Entity Linking is Slow

- Check `EL_MAX_WORKERS` - increase if API allows
- Reduce `EL_LIMIT` to fewer candidates per entity
- Increase `EL_SCORE_THRESHOLD` to filter out weak matches

### Entities Not Merging

- Lower `EL_SCORE_THRESHOLD` (default 0.85 is conservative)
- Check LLM prompt in `entity_linking/linker.py` - may be too strict
- Verify entity names/aliases are similar enough for vector search

### Neo4j Import Fails

- Check Neo4j is running: `docker compose logs neo4j`
- Verify data format in `data/import_linked/*_kg.json`
- Check Neo4j credentials in `.env`

### API Returns 500 Error

- Check backend logs: `uvicorn backend.app.main:app --reload`
- Verify Neo4j connection: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- Check Cypher query syntax in router

### Frontend Can't Connect to Backend

- Verify backend is running on port 8000
- Check CORS configuration in `backend/app/main.py`
- Verify API URL in `frontend/src/services/api.js`

---

## Testing

### Python Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run single test file
python -m pytest tests/test_linker.py -v

# Run specific test
python -m pytest tests/test_linker.py::test_entity_link_iteration -v
```

### Frontend Tests

```bash
cd frontend

# Run all tests
npm test

# Run single test file
npx vitest run src/components/Graph.test.jsx

# Watch mode
npx vitest
```

### Manual Testing

1. Place test markdown files in `data/raw/uet/`
2. Run extraction: `./run.sh extract`
3. Check output in `data/extracted/`
4. Run entity linking: `./run.sh link`
5. Check output in `data/import_linked/`
6. Import to Neo4j: `./run.sh import`
7. Query via Neo4j Browser or API

---

## Related Documentation

- **AGENTS.md** - Detailed code style guidelines, naming conventions, and patterns
- **entity_linking/README.md** - Deep dive into entity linking algorithm and configuration
- **entity_linking/entity_linking_pipeline.md** - Entity linking workflow details
- **entity_linking/entity_linking_technical_deep_dive.md** - Technical analysis

---

## Key Insights for Future Development

1. **Schema is King:** The strict entity/relationship schema prevents hallucination and ensures consistency. Respect it.

2. **Vector + LLM Hybrid:** Vector similarity finds candidates fast, LLM makes accurate decisions. Don't skip either step.

3. **Idempotency Matters:** All operations (extraction, linking, import) should be re-runnable without side effects.

4. **Concurrency is Critical:** With large datasets, ThreadPoolExecutor parallelization makes the difference between hours and minutes.

5. **Audit Trail:** The `merged_ids` field tracks entity history. Preserve it for debugging and compliance.

6. **Configuration Over Code:** Use environment variables for tuning (thresholds, workers, iterations) rather than hardcoding.

7. **Multi-Provider LLM:** The factory pattern allows switching between Gemini, ProxyPal, and Ollama without code changes. Leverage this for cost/latency optimization.