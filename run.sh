#!/usr/bin/env bash
set -euo pipefail

# --- CONFIG ---
RAW_DIR="${RAW_DIR:-data/raw/uet}"
EXTRACTED_DIR="${EXTRACTED_DIR:-data/extracted}"
LINKED_DIR="${LINKED_DIR:-data/import_linked}"
# LINKED_DIR="${LINKED_DIR:-data/extracted}"

echo "Starting Docker services..."
docker compose up -d

echo "Ollama: http://localhost:11434"
echo "Neo4j: http://localhost:7474"
echo "Bolt: bolt://localhost:7687"
echo "Qdrant Web UI: http://localhost:6333/dashboard"

# --- CORE FUNCTIONS ---
do_extract() {
    echo "[*] Extracting from $RAW_DIR..."
    python3 -m extract.extractor
}

# do_entity_link() {
#     echo "[*] Linking entities: $EXTRACTED_DIR -> $LINKED_DIR"
#     EL_KG_DIR="$EXTRACTED_DIR" \
#     EL_OUTPUT_DIR="$LINKED_DIR" \
#     python3 -m entity_linking.cli
# }
do_entity_link() {
    echo "[*] Linking entities: $EXTRACTED_DIR -> $LINKED_DIR"
    EL_KG_DIR="$EXTRACTED_DIR" \
    EL_OUTPUT_DIR="$LINKED_DIR" \
    EL_SCORE_THRESHOLD="${EL_SCORE_THRESHOLD:-0.85}" \
    EL_MAX_WORKERS="${EL_MAX_WORKERS:-8}" \
    EL_LOG_LEVEL="${EL_LOG_LEVEL:-INFO}" \
    PYTHONUNBUFFERED=1 \
    python3 -m entity_linking.cli
}

do_import() {
    local import_dir="${1:-$LINKED_DIR}"
    echo "[*] Importing from $import_dir..."
    python3 neo4j/scripts/import_to_neo4j.py --dir "$import_dir"
}

do_run() {
    echo "[*] Running full pipeline..."
    do_extract
    do_entity_link
    do_import "$LINKED_DIR"
}

# --- EXECUTION LOGIC ---
if [ -z "${1:-}" ]; then
    echo -e "Choose an action:\n 1) Extract entities\n 2) Link entities\n 3) Import to Neo4j\n 4) Run All\n 5) Exit (Services only)"
    read -p "Select [1-5]: " choice

    case $choice in
        1) do_extract ;;
        2) do_entity_link ;;
        3) do_import ;;
        4) do_run ;;
        5) echo "Services started. Exiting." ;;
        *) echo "[-] Invalid choice."; exit 1 ;;
    esac
else
    case "$1" in
        extract) do_extract ;;
        link)    do_entity_link ;;
        import)  do_import "${2:-$LINKED_DIR}" ;;
        run)     do_run ;;
        *) echo "Usage: ./run.sh {extract | link | import [dir] | run}"; exit 1 ;;
    esac
fi