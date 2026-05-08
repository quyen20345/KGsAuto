# KGsAuto Chat API

Standalone chatbot API for the product-facing chat experience. It wraps `services.rag_system` and does not depend on the legacy `apps/rag_api` service.

## Run locally

```bash
uvicorn apps.chat_api.main:app --host 0.0.0.0 --port 8002 --reload
```

## Endpoints

```text
GET  /health
GET  /modes
POST /query
```

## Query example

```bash
curl -X POST http://localhost:8002/query \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hiệu trưởng là ai?",
    "mode": "semantic_search",
    "top_k": 5,
    "include_evidence": true
  }'
```

## Mode prerequisites

- `semantic_search`: Qdrant running, collection created, markdown indexed.
- `graph_search` / `naive_grag`: Neo4j running with imported graph.
- `hybrid`: both Qdrant markdown indexing and Neo4j graph data.
