#!/usr/bin/env bash
set -euo pipefail

echo "Starting Docker services..."
docker compose up -d

echo "Ollama: http://localhost:11434"
echo "Neo4j: http://localhost:7474"
echo "Bolt: bolt://localhost:7687"
echo "Qdrant Web UI: http://localhost:6333/dashboard"

# Extract knowledge graphs from markdown
python3 -m services.extraction.extract

# Import to Neo4j
python3 -m services.neo4j_import.import_to_neo4j --dir "data/extracted"

# Start frontend (in background)
cd apps/frontend && npm run dev &

# Start backend
cd ../..
uvicorn apps.graph_api.main:app --host 0.0.0.0 --port 8000 --reload

# docker compose down
