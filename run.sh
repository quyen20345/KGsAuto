#!/usr/bin/env bash
set -euo pipefail

echo "Starting Docker services..."
docker compose up -d

echo "Ollama: http://localhost:11434"
echo "Neo4j: http://localhost:7474"
echo "Bolt: bolt://localhost:7687"
echo "Qdrant Web UI: http://localhost:6333/dashboard"

# --- CORE FUNCTIONS ---
do_extract() { 
    local d="${1:-data/uet}"
    echo "[*] Extracting..."
    python3 -m extract.extractor
}


do_entity_link() { 
    echo "[*] Linking entities..."
    python3 -m entity_linking.entity_store
}


do_import() { 
    local d="${1:-neo4j/import}"
    echo "[*] Importing from $d..."
    python3 neo4j/scripts/import_to_neo4j.py --dir "$d"
}


do_run() { 
    echo "[*] Running full pipeline..."
    do_extract
    do_entity_link
    do_import
}

# --- EXECUTION LOGIC ---
if [ -z "${1:-}" ]; then
    # Interactive Menu
    echo -e "Choose an action:\n 1) Extract entities\n 2) Link entities\n 3) Import to Neo4j\n 4) Run All\n 5) Exit (Services only)"
    read -p "Select [1-5]: " choice
    
    case $choice in
        1) do_extract ;;
        2) do_entity_link ;;
        3) read -p "Directory [default: neo4j/import]: " d; do_import "${d:-neo4j/import}" ;;
        4) do_run ;;
        5) echo "Services started. Exiting." ;;
        *) echo "[-] Invalid choice."; exit 1 ;;
    esac
else
    # CLI Arguments
    case "$1" in
        extract) do_extract ;;
        link)    do_entity_link ;;
        import)  do_import "${2:-neo4j/import}" ;;
        run)     do_run ;;
        *) echo "Usage: ./run.sh {extract | link | import [dir] | run}"; exit 1 ;;
    esac
fi