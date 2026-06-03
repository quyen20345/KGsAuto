#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

usage() {
  echo "Usage: ./run.sh [dev|api|frontend|docker]"
  echo ""
  echo "  dev       Start all 4 services locally (APIs + frontend)"
  echo "  api       Start 3 API services only (graph, pipeline, chat)"
  echo "  frontend  Start frontend dev server only"
  echo "  docker    Start full stack with Docker Compose"
  exit 0
}

MODE="${1:-dev}"
case "$MODE" in
  -h|--help|help) usage ;;
  dev|api|frontend) ;;
  docker)
    echo "Starting full stack with Docker Compose..."
    docker compose up -d
    echo
    echo "Services:"
    echo "  Frontend:          http://localhost:3000"
    echo "  Neo4j Browser:     http://localhost:7474"
    echo "  Qdrant Dashboard:  http://localhost:6333/dashboard"
    exit 0
    ;;
  *) echo "Unknown mode: $MODE"; usage ;;
esac

PIDS=()

cleanup() {
  trap - EXIT INT TERM
  echo ""
  echo "Stopping services..."
  for pid in "${PIDS[@]:-}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
  wait 2>/dev/null || true
}

trap cleanup EXIT INT TERM

start_service() {
  local name="$1"; shift
  echo "Starting $name..."
  "$@" &
  PIDS+=("$!")
}

if [[ "$MODE" == "dev" || "$MODE" == "api" ]]; then
  start_service "Graph API    :8000" \
    uvicorn apps.graph_api.main:app --host 0.0.0.0 --port 8000 --reload
  start_service "Pipeline API :8001" \
    uvicorn apps.pipeline_api.main:app --host 0.0.0.0 --port 8001 --reload
  start_service "Chat API     :8002" \
    uvicorn apps.chat_api.main:app --host 0.0.0.0 --port 8002 --reload
fi

if [[ "$MODE" == "dev" || "$MODE" == "frontend" ]]; then
  start_service "Frontend     :5173" \
    bash -lc 'cd apps/frontend && npm install -s 2>/dev/null; npm run dev -- --host 0.0.0.0'
fi

echo ""
echo "URLs:"
[[ "$MODE" == "dev" || "$MODE" == "api" ]] && echo "  Graph API Docs:    http://localhost:8000/docs"
[[ "$MODE" == "dev" || "$MODE" == "api" ]] && echo "  Pipeline API Docs: http://localhost:8001/docs"
[[ "$MODE" == "dev" || "$MODE" == "api" ]] && echo "  Chat API Docs:     http://localhost:8002/docs"
[[ "$MODE" == "dev" || "$MODE" == "frontend" ]] && echo "  Frontend:          http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop."

wait -n "${PIDS[@]}"
