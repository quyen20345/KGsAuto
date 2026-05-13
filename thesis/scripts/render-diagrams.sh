#!/usr/bin/env bash
# render-diagrams.sh
# Render all Mermaid diagrams to PNG for thesis.
# Run from: thesis/scripts/   or   cd thesis && ./scripts/render-diagrams.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THESIS_DIR="$(dirname "$SCRIPT_DIR")"
IMAGE_DIR="$THESIS_DIR/image"

MMDC="${MMDC:-/snap/bin/mmdc}"

if [ ! -x "$MMDC" ]; then
  echo "ERROR: mmdc not found at $MMDC" >&2
  echo "Install with: sudo snap install mermaid-cli" >&2
  exit 1
fi

mkdir -p "$IMAGE_DIR/generated/chapter3" \
  "$IMAGE_DIR/generated/chapter4" \
  "$IMAGE_DIR/generated/chapter5" \
  "$IMAGE_DIR/generated/chapter6"

echo "=== Rendering Chapter 3 diagrams ==="

"$MMDC" -i "$IMAGE_DIR/diagrams/chapter3/architecture-overview.mmd" \
  -o "$IMAGE_DIR/generated/chapter3/architecture-overview.png" \
  -w 1400 -H 1000 -b white

echo "=== Rendering Chapter 4 diagrams ==="

"$MMDC" -i "$IMAGE_DIR/diagrams/chapter4/extraction-pipeline.mmd" \
  -o "$IMAGE_DIR/generated/chapter4/extraction-pipeline.png" \
  -w 1200 -H 800

"$MMDC" -i "$IMAGE_DIR/diagrams/chapter4/filename-clustering.mmd" \
  -o "$IMAGE_DIR/generated/chapter4/filename-clustering.png" \
  -w 1600 -H 1100 -b white

"$MMDC" -i "$IMAGE_DIR/diagrams/chapter4/graph-schema.mmd" \
  -o "$IMAGE_DIR/generated/chapter4/graph-schema.png" \
  -w 1200 -H 600

echo "=== Rendering Chapter 5 diagrams ==="

"$MMDC" -i "$IMAGE_DIR/diagrams/chapter5/er-pipeline-overview.mmd" \
  -o "$IMAGE_DIR/generated/chapter5/er-pipeline-overview.png" \
  -w 1400 -H 700 -b white

"$MMDC" -i "$IMAGE_DIR/diagrams/chapter5/er-resolution-concept.mmd" \
  -o "$IMAGE_DIR/generated/chapter5/er-resolution-concept.png" \
  -w 1400 -H 800 -b white

"$MMDC" -i "$IMAGE_DIR/diagrams/chapter5/er-stage1-normalization.mmd" \
  -o "$IMAGE_DIR/generated/chapter5/er-stage1-normalization.png" \
  -w 1400 -H 900 -b white

"$MMDC" -i "$IMAGE_DIR/diagrams/chapter5/er-stage2-blocking.mmd" \
  -o "$IMAGE_DIR/generated/chapter5/er-stage2-blocking.png" \
  -w 1400 -H 1000 -b white

"$MMDC" -i "$IMAGE_DIR/diagrams/chapter5/er-two-pass-llm.mmd" \
  -o "$IMAGE_DIR/generated/chapter5/er-two-pass-llm.png" \
  -w 1400 -H 1000 -b white

"$MMDC" -i "$IMAGE_DIR/diagrams/chapter5/er-conservative-fallback.mmd" \
  -o "$IMAGE_DIR/generated/chapter5/er-conservative-fallback.png" \
  -w 1200 -H 800 -b white

echo "=== Rendering Chapter 6 diagrams ==="

"$MMDC" -i "$IMAGE_DIR/diagrams/chapter6/rag-modes-overview.mmd" \
  -o "$IMAGE_DIR/generated/chapter6/rag-modes-overview.png" \
  -w 1500 -H 900 -b white

"$MMDC" -i "$IMAGE_DIR/diagrams/chapter6/hybrid-rag-fusion.mmd" \
  -o "$IMAGE_DIR/generated/chapter6/hybrid-rag-fusion.png" \
  -w 1400 -H 700 -b white

"$MMDC" -i "$IMAGE_DIR/diagrams/chapter6/semantic-search-flow.mmd" \
  -o "$IMAGE_DIR/generated/chapter6/semantic-search-flow.png" \
  -w 1400 -H 500 -b white

"$MMDC" -i "$IMAGE_DIR/diagrams/chapter6/naive-graph-rag-flow.mmd" \
  -o "$IMAGE_DIR/generated/chapter6/naive-graph-rag-flow.png" \
  -w 1500 -H 500 -b white

"$MMDC" -i "$IMAGE_DIR/diagrams/chapter6/graph-search-flow.mmd" \
  -o "$IMAGE_DIR/generated/chapter6/graph-search-flow.png" \
  -w 1800 -H 1100 -b white

echo "=== All diagrams rendered successfully ==="
