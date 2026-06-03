#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

usage() {
  echo "Usage: ./run.sh [dev|api|frontend|docker|setup]"
  echo ""
  echo "  setup     Cài đặt dependencies (conda py312 + pip + frontend npm)"
  echo "  dev       Chạy tất cả 4 services (APIs + frontend)"
  echo "  api       Chạy 3 API services (graph, pipeline, chat)"
  echo "  frontend  Chạy frontend dev server"
  echo "  docker    Khởi động full stack bằng Docker Compose"
  exit 0
}

MODE="${1:-dev}"
case "$MODE" in
  -h|--help|help) usage ;;
  dev|api|frontend) ;;
  setup)
    echo "=== Cài đặt dependencies ==="
    echo ""

    # Python
    if command -v conda &>/dev/null; then
      echo "[1/4] Activating conda py312..."
      source "$(conda info --base)/etc/profile.d/conda.sh" 2>/dev/null || true
      conda activate py312 2>/dev/null || {
        echo "  Creating conda env py312..."
        conda create -n py312 python=3.12 -y
        conda activate py312
      }
    fi

    echo "[2/4] Installing Python packages..."
    pip install -r requirements.txt
    pip install -e . --no-deps

    # Frontend
    echo "[3/4] Installing frontend dependencies..."
    cd apps/frontend && npm install && cd "$ROOT_DIR"

    # Neo4j + Qdrant
    echo "[4/4] Starting infrastructure (Neo4j + Qdrant)..."
    docker compose up -d neo4j qdrant 2>/dev/null || echo "  Docker compose not available or already running"

    echo ""
    echo "=== Setup hoàn tất ==="
    echo "Chạy:  ./run.sh dev"
    exit 0
    ;;
  docker)
    echo "Starting full stack with Docker Compose..."
    docker compose up -d
    echo ""
    echo "Services:"
    echo "  Frontend:          http://localhost:3000"
    echo "  Neo4j Browser:     http://localhost:7474"
    echo "  Qdrant Dashboard:  http://localhost:6333/dashboard"
    exit 0
    ;;
  *) echo "Unknown mode: $MODE"; usage ;;
esac

# Auto-detect conda env
if command -v conda &>/dev/null && [[ "${CONDA_DEFAULT_ENV:-}" != "py312" ]]; then
  echo "Warning: conda env 'py312' not active. Run: conda activate py312"
  echo "         Or run: ./run.sh setup"
fi

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
    bash -lc 'cd '"$ROOT_DIR"'/apps/frontend && npm run dev -- --host 0.0.0.0'
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
