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

(cd "$IMAGE_DIR/diagrams/chapter3" && \
  pdflatex -interaction=nonstopmode architecture-overview.tex && \
  pdftoppm -png -r 300 -singlefile architecture-overview.pdf \
    "$IMAGE_DIR/generated/chapter3/architecture-overview" && \
  rm -f architecture-overview.aux architecture-overview.log architecture-overview.pdf)

echo "=== Rendering Chapter 4 diagrams ==="

(cd "$IMAGE_DIR/diagrams/chapter4" && \
  pdflatex -interaction=nonstopmode extraction-pipeline.tex && \
  pdftoppm -png -r 300 -singlefile extraction-pipeline.pdf \
    "$IMAGE_DIR/generated/chapter4/extraction-pipeline" && \
  rm -f extraction-pipeline.aux extraction-pipeline.log extraction-pipeline.pdf)

(cd "$IMAGE_DIR/diagrams/chapter4" && \
  pdflatex -interaction=nonstopmode filename-clustering.tex && \
  pdftoppm -png -r 300 -singlefile filename-clustering.pdf \
    "$IMAGE_DIR/generated/chapter4/filename-clustering" && \
  rm -f filename-clustering.aux filename-clustering.log filename-clustering.pdf)

"$MMDC" -i "$IMAGE_DIR/diagrams/chapter4/graph-schema.mmd" \
  -o "$IMAGE_DIR/generated/chapter4/graph-schema.png" \
  -w 1200 -H 600

node "$SCRIPT_DIR/render-diagrams.js" \
  "$IMAGE_DIR/static/kg_prompt.html" \
  "$IMAGE_DIR/generated/chapter4/kg_prompt.png"

echo "=== Rendering Chapter 5 diagrams ==="

for TEX_DIAGRAM in \
  er-pipeline-overview \
  er-resolution-concept \
  er-stage1-normalization \
  er-stage2-blocking; do
  (cd "$IMAGE_DIR/diagrams/chapter5" && \
    pdflatex -interaction=nonstopmode "$TEX_DIAGRAM.tex" && \
    pdftoppm -png -r 300 -singlefile "$TEX_DIAGRAM.pdf" \
      "$IMAGE_DIR/generated/chapter5/$TEX_DIAGRAM" && \
    rm -f "$TEX_DIAGRAM.aux" "$TEX_DIAGRAM.log" "$TEX_DIAGRAM.pdf")
done

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
