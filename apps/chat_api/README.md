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
GET  /v1/models
POST /v1/chat/completions
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

## OpenAI-compatible adapter for external chat UIs

The API also exposes an OpenAI-compatible surface so reusable UIs such as
[`mckaywrigley/chatbot-ui`](https://github.com/mckaywrigley/chatbot-ui) can talk
to KGsAuto without changing their chat request format.

```bash
curl -X POST http://localhost:8002/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "semantic_search",
    "messages": [{"role": "user", "content": "Hiệu trưởng là ai?"}],
    "stream": false,
    "include_evidence": true
  }'
```

Supported model IDs map to KGsAuto RAG modes:

```bash
curl http://localhost:8002/v1/models
```

For `chatbot-ui`, point its OpenAI-compatible base URL to:

```text
http://localhost:8002/v1
```

and use one of these model IDs:

```text
semantic_search
graph_search
naive_grag
hybrid
```

`stream=true` is supported using Server-Sent Events. The RAG pipeline currently
returns a complete answer first, so streaming is simulated from the final answer.
