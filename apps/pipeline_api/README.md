# KGsAuto Pipeline API

`apps/pipeline_api` orchestrates the document-to-graph workflow used by the frontend `/pipeline/*` pages. It manages raw Markdown files, optional crawling, pipeline run history, cancellation, and live run events.

## Overview

```mermaid
flowchart TB
    UI[Frontend /pipeline] --> API[Pipeline API :8001]

    API --> Files[File routes]
    API --> Crawl[Crawl route]
    API --> Runs[Pipeline routes]
    API --> Events[SSE events]

    Files --> Raw[(data/raw/uet)]
    Files --> Extracted[(data/extracted)]
    Files --> Artifacts[(data/entity_resolution/artifacts)]
    Crawl --> Raw

    Runs --> Runner[runner.py]
    Runner --> Extraction[services.extraction.cli]
    Runner --> EntityResolution[services.entity_resolution.cli]
    Runner --> Import[services.neo4j_import.import_to_neo4j]
    Runner --> DB[(SQLite run DB)]
    Events --> UI
```

## Run locally

Run from the repository root after starting the local infrastructure with `docker compose up -d`.

```bash
uvicorn apps.pipeline_api.main:app --host 0.0.0.0 --port 8001 --reload
```

Useful URLs:

- API docs: http://localhost:8001/docs
- Health: http://localhost:8001/api/health

## Routes

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Service health check |

### Files

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/files/raw` | List raw Markdown files and whether each has extracted KG output |
| `GET` | `/api/files/extracted` | List extracted `*_kg.json` files with node/relationship counts when readable |
| `GET` | `/api/files/resolved` | List entity-resolution artifact runs and stage availability |
| `POST` | `/api/files/upload` | Upload one or more raw Markdown files |
| `DELETE` | `/api/files/raw/{filename}` | Delete a raw Markdown file by safe filename |

### Crawl

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/crawl` | Crawl URLs into the raw Markdown directory |

### Pipeline runs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/pipeline/run` | Start a pipeline run |
| `GET` | `/api/pipeline/runs` | List recent runs |
| `GET` | `/api/pipeline/runs/{run_id}` | Get run detail and recent logs |
| `POST` | `/api/pipeline/runs/{run_id}/cancel` | Cancel the active run |
| `GET` | `/api/pipeline/runs/{run_id}/events` | Stream status/log events as `text/event-stream` |

## Run modes

`POST /api/pipeline/run` accepts `mode` as either `quick_import` or `full_pipeline`.

```mermaid
flowchart LR
    Raw[Raw Markdown] --> Extraction[Extraction]
    Extraction --> Extracted[Extracted KG JSON]

    Extracted -->|quick_import| ImportQuick[Neo4j import]
    Extracted -->|full_pipeline| ER[Entity resolution]
    ER --> Resolved[Stage 3 output graph]
    Resolved --> ImportFull[Neo4j import]

    ImportQuick --> Neo4j[(Neo4j)]
    ImportFull --> Neo4j
```

- `quick_import`: runs `services.extraction.cli`, then imports `data/extracted` directly into Neo4j.
- `full_pipeline`: runs extraction, runs `services.entity_resolution.cli --stage all --store-backend qdrant`, then imports `data/entity_resolution/artifacts/{run_id}/stage3/output_graph` into Neo4j.

Only one active run is reserved at a time. A second trigger returns a conflict until the current run completes, fails, or is cancelled.

## Event stream

The frontend subscribes with `EventSource` to `/api/pipeline/runs/{run_id}/events`.

```mermaid
sequenceDiagram
    autonumber
    participant UI as Frontend /pipeline
    participant API as Pipeline API
    participant Runner as runner.py
    participant DB as SQLite
    participant Services as Extraction/ER/Import

    UI->>API: POST /api/pipeline/run
    API->>Runner: reserve_run(run_id)
    API-->>UI: run_id + pending
    UI->>API: GET /api/pipeline/runs/{run_id}/events

    Runner->>DB: create/update run rows
    Runner->>Services: run subprocess steps
    Services-->>Runner: stdout/stderr lines
    Runner->>DB: append logs
    Runner-->>API: status/log events
    API-->>UI: SSE data events

    Runner->>DB: completed/failed status
    API-->>UI: terminal status event
```

Event payloads are JSON encoded in `data:` lines. Idle streams emit `{"type": "ping"}` keepalive events.
