# Repository Guidelines

## Project Structure
KGsAuto is a Python/React knowledge-graph system. FastAPI apps live in `apps/`: `apps/backend` is the main graph API and `apps/rag_api` is the unified retrieval/RAG API. Core packages are in `services/`: `entity_resolution`, `rag_system`, `llms`, `crawler`, `extraction`.

- `services/rag_system/`: Unified RAG with `pipeline.py` (main entry), `modes/` (semantic_search, graph_search, naive_grag, hybrid), `storage/`, `retrieval/`, `graph/`, `workflows/graph_search/`, `evaluation/`. Read `services/rag_system/README.md` for detailed architecture.
- `services/extraction/`: Extracts knowledge graphs from documents via CLI (`python -m services.extraction.cli`).
- `services/entity_resolution/`: 3-stage entity resolution pipeline via CLI (`python -m services.entity_resolution.cli --stage all`).
- `apps/frontend/src/`: Vite React UI with components in `components/` and pages in `pages/`.
- `data/`: Generated artifacts and extracted data.

## Developer Commands

### Infrastructure
```bash
docker compose up -d          # Start Neo4j, Qdrant, Ollama
docker compose down           # Stop infra
```

### APIs
```bash
uvicorn apps.backend.app.main:app --host 0.0.0.0 --port 8000 --reload
uvicorn apps.rag_api.main:app --host 0.0.0.0 --port 8001 --reload
```

### RAG CLI (services/rag_system)
```bash
python -m services.rag_system.cli test-connections
python -m services.rag_system.cli create-collection
python -m services.rag_system.cli index --limit 100
python -m services.rag_system.cli query --question "Hiệu trưởng là ai?" --mode semantic_search --top-k 5 --show-evidence
python -m services.rag_system.cli evaluate run --dataset <jsonl> --output <jsonl> --mode semantic_search --top-k 5
```

### Extraction CLI (services/extraction)
```bash
python -m services.extraction.cli --input-dir data/raw/uet --output-dir data/extracted --provider OpenAICompatible --model cx/gpt-5.3-codex
python -m services.extraction.cli --input-dir data/raw/uet --output-dir data/extracted --provider OpenAICompatible --model cx/gpt-5.3-codex --no-skip-existing
```

### Entity Resolution CLI (services/entity_resolution)
```bash
# Run all 3 stages with memory backend (fast, non-persistent)
python -m services.entity_resolution.cli --stage all --input-dir data/extracted --store-backend memory --run-id demo_run

# Run with qdrant backend for persistence between stages
python -m services.entity_resolution.cli --stage stage1 --input-dir data/extracted --store-backend qdrant --run-id my_run
python -m services.entity_resolution.cli --stage stage2 --store-backend qdrant --run-id my_run
python -m services.entity_resolution.cli --stage stage3 --store-backend qdrant --run-id my_run
```

### Neo4j Import
```bash
python apps/backend/neo4j/scripts/import_to_neo4j.py --dir data/entity_resolution/artifacts/final/stage3/output_graph
python -m apps.backend.neo4j.scripts.add_embeddings_to_neo4j
python -m apps.backend.neo4j.scripts.create_vector_index
```

### Frontend
```bash
cd apps/frontend && npm install && npm run dev  # dev server at localhost:5173
cd apps/frontend && npm run build               # production build
cd apps/frontend && npm run lint                # ESLint
```

### Testing
```bash
conda run -n py312 python -m pytest services/rag_system/tests apps/rag_api/tests -q
```

## Coding Style
- Python 3.10+, 4-space indentation, `snake_case` functions/modules, `PascalCase` classes and Pydantic models.
- React: `PascalCase` component files, route views in `pages/`, API calls in `src/services/api.js`.
- Keep API routers thin; put reusable logic in `services/`.

## Testing
- Use `pytest`. Test files: `services/rag_system/tests/`, `apps/rag_api/tests/`, `apps/backend/tests/`. Name files `test_*.py`.
- For frontend changes, run `npm run lint`.

## Security
- Do not commit secrets. Copy `.env.example` files for setup. Keep keys in `.env`.