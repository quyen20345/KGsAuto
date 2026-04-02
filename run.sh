#!/usr/bin/env bash
set -euo pipefail
# RAW_DIR="${RAW_DIR:-data/raw/uet}"
# EXTRACTED_DIR="${EXTRACTED_DIR:-data/extracted}"
# LINKED_DIR="${LINKED_DIR:-data/import_linked}"
# LINKED_DIR="${LINKED_DIR:-data/extracted_v2}"


echo "Starting Docker services..."
docker compose up -d

echo "Ollama: http://localhost:11434"
echo "Neo4j: http://localhost:7474"
echo "Bolt: bolt://localhost:7687"
echo "Qdrant Web UI: http://localhost:6333/dashboard"

# Run services (Ollama, Neo4j, Qdrant)
docker compose up -d

python3 -m extractv2.extractv2

# EL_KG_DIR="data/extracted" EL_OUTPUT_DIR="data/import_linked" python3 -m entity_linking.cli


python3 neo4j/scripts/import_to_neo4j.py --dir "data/extracted_v2"

npm run dev

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# docker compose down