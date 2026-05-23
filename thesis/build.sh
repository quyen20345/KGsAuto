#!/bin/bash
# Build thesis with logging
set -uo pipefail

# Tạo thư mục logs nếu chưa có
mkdir -p logs

# Tạo tên file log với timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOGFILE="logs/build_${TIMESTAMP}.log"

echo "Building thesis..." | tee "$LOGFILE"
echo "Log file: $LOGFILE" | tee -a "$LOGFILE"
echo "---" | tee -a "$LOGFILE"

# # ── Step 0: Render diagrams ──────────────────────────────────────────
echo "[0/4] Rendering diagrams..." | tee -a "$LOGFILE"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THESIS_DIR="$SCRIPT_DIR"
IMAGE_DIR="$THESIS_DIR/image"
MMDC="${MMDC:-mmdc}"

if ! command -v "$MMDC" &>/dev/null; then
  echo "  ⚠ mmdc not found, skipping diagram rendering" | tee -a "$LOGFILE"
else
  mkdir -p "$IMAGE_DIR/generated/chapter3" \
    "$IMAGE_DIR/generated/chapter4" \
    "$IMAGE_DIR/generated/chapter5" \
    "$IMAGE_DIR/generated/chapter6"

#   # Chapter 3 — architecture-overview (TikZ standalone → PDF → PNG)
#   (cd "$IMAGE_DIR/diagrams/chapter3" && \
#     pdflatex -interaction=nonstopmode architecture-overview.tex && \
#     pdftoppm -png -r 300 -singlefile architecture-overview.pdf \
#       "$IMAGE_DIR/generated/chapter3/architecture-overview" && \
#     rm -f architecture-overview.aux architecture-overview.log architecture-overview.pdf) >> "$LOGFILE" 2>&1
#   (cd "$IMAGE_DIR/diagrams/chapter3" && \
#     pdflatex -interaction=nonstopmode architecture-overview.tex && \
#     pdftoppm -png -r 300 -singlefile architecture-overview.pdf \
#       "$IMAGE_DIR/generated/chapter3/architecture-overview" && \
#     rm -f architecture-overview.aux architecture-overview.log architecture-overview.pdf) >> "$LOGFILE" 2>&1
#   # Chapter 4 — extraction-pipeline (TikZ standalone → PDF → PNG)
#   (cd "$IMAGE_DIR/diagrams/chapter4" && \
#     pdflatex -interaction=nonstopmode extraction-pipeline.tex && \
#     pdftoppm -png -r 300 -singlefile extraction-pipeline.pdf \
#       "$IMAGE_DIR/generated/chapter4/extraction-pipeline" && \
#     rm -f extraction-pipeline.aux extraction-pipeline.log extraction-pipeline.pdf) >> "$LOGFILE" 2>&1

#   "$MMDC" -i "$IMAGE_DIR/diagrams/chapter4/graph-schema.mmd" \
#     -o "$IMAGE_DIR/generated/chapter4/graph-schema.png" \
#     -w 1200 -H 600 >> "$LOGFILE" 2>&1

#   # Chapter 5 — er-pipeline-overview (TikZ standalone → PDF → PNG)
#   (cd "$IMAGE_DIR/diagrams/chapter5" && \
#     pdflatex -interaction=nonstopmode er-pipeline-overview.tex && \
#     pdftoppm -png -r 300 -singlefile er-pipeline-overview.pdf \
#       "$IMAGE_DIR/generated/chapter5/er-pipeline-overview" && \
#     rm -f er-pipeline-overview.aux er-pipeline-overview.log er-pipeline-overview.pdf) >> "$LOGFILE" 2>&1

#   (cd "$IMAGE_DIR/diagrams/chapter5" && \
#     pdflatex -interaction=nonstopmode er-resolution-concept.tex && \
#     pdftoppm -png -r 300 -singlefile er-resolution-concept.pdf \
#       "$IMAGE_DIR/generated/chapter5/er-resolution-concept" && \
#     rm -f er-resolution-concept.aux er-resolution-concept.log er-resolution-concept.pdf) >> "$LOGFILE" 2>&1

#   # Chapter 5 — TikZ standalone diagrams
#   (cd "$IMAGE_DIR/diagrams/chapter5" && \
#     pdflatex -interaction=nonstopmode er-stage1-normalization.tex && \
#     pdftoppm -png -r 300 -singlefile er-stage1-normalization.pdf \
#       "$IMAGE_DIR/generated/chapter5/er-stage1-normalization" && \
#     rm -f er-stage1-normalization.aux er-stage1-normalization.log er-stage1-normalization.pdf) >> "$LOGFILE" 2>&1

#   (cd "$IMAGE_DIR/diagrams/chapter5" && \
#     pdflatex -interaction=nonstopmode er-stage2-blocking.tex && \
#     pdftoppm -png -r 300 -singlefile er-stage2-blocking.pdf \
#       "$IMAGE_DIR/generated/chapter5/er-stage2-blocking" && \
#     rm -f er-stage2-blocking.aux er-stage2-blocking.log er-stage2-blocking.pdf) >> "$LOGFILE" 2>&1

#   # Chapter 6
#   # Chapter 6 — rag-modes-overview (TikZ standalone → PDF → PNG)
#   (cd "$IMAGE_DIR/diagrams/chapter6" && \
#     pdflatex -interaction=nonstopmode rag-modes-overview.tex && \
#     pdftoppm -png -r 300 -singlefile rag-modes-overview.pdf \
#       "$IMAGE_DIR/generated/chapter6/rag-modes-overview" && \
#     rm -f rag-modes-overview.aux rag-modes-overview.log rag-modes-overview.pdf) >> "$LOGFILE" 2>&1

#   # Chapter 6 — hybrid-rag-fusion (TikZ standalone → PDF → PNG)
#   (cd "$IMAGE_DIR/diagrams/chapter6" && \
#     pdflatex -interaction=nonstopmode hybrid-rag-fusion.tex && \
#     pdftoppm -png -r 300 -singlefile hybrid-rag-fusion.pdf \
#       "$IMAGE_DIR/generated/chapter6/hybrid-rag-fusion" && \
#     rm -f hybrid-rag-fusion.aux hybrid-rag-fusion.log hybrid-rag-fusion.pdf) >> "$LOGFILE" 2>&1

#   # Chapter 6 — semantic-search-flow (TikZ standalone → PDF → PNG)
#   (cd "$IMAGE_DIR/diagrams/chapter6" && \
#     pdflatex -interaction=nonstopmode semantic-search-flow.tex && \
#     pdftoppm -png -r 300 -singlefile semantic-search-flow.pdf \
#       "$IMAGE_DIR/generated/chapter6/semantic-search-flow" && \
#     rm -f semantic-search-flow.aux semantic-search-flow.log semantic-search-flow.pdf) >> "$LOGFILE" 2>&1

#   # Chapter 6 — naive-graph-rag-flow (TikZ standalone → PDF → PNG)
#   (cd "$IMAGE_DIR/diagrams/chapter6" && \
#     pdflatex -interaction=nonstopmode naive-graph-rag-flow.tex && \
#     pdftoppm -png -r 300 -singlefile naive-graph-rag-flow.pdf \
#       "$IMAGE_DIR/generated/chapter6/naive-graph-rag-flow" && \
#     rm -f naive-graph-rag-flow.aux naive-graph-rag-flow.log naive-graph-rag-flow.pdf) >> "$LOGFILE" 2>&1

#   # Chapter 6 — graph-search-flow (TikZ standalone → PDF → PNG)
#   (cd "$IMAGE_DIR/diagrams/chapter6" && \
#     pdflatex -interaction=nonstopmode graph-search-flow.tex && \
#     pdftoppm -png -r 300 -singlefile graph-search-flow.pdf \
#       "$IMAGE_DIR/generated/chapter6/graph-search-flow" && \
#     rm -f graph-search-flow.aux graph-search-flow.log graph-search-flow.pdf) >> "$LOGFILE" 2>&1

#   echo "  ✓ Diagrams rendered" | tee -a "$LOGFILE"
# fi

# mkdir -p "$IMAGE_DIR/generated/chapter4"
# node "$THESIS_DIR/scripts/render-diagrams.js" \
#   "$IMAGE_DIR/static/kg_prompt.html" \
#   "$IMAGE_DIR/generated/chapter4/kg_prompt.png" >> "$LOGFILE" 2>&1

fi

# ── Step 1: pdflatex pass 1 ──────────────────────────────────────────────────
echo "[1/4] Running pdflatex (pass 1)..." | tee -a "$LOGFILE"
pdflatex -interaction=nonstopmode main.tex >> "$LOGFILE" 2>&1

# ── Step 2: bibtex ───────────────────────────────────────────────────────────
echo "[2/4] Running bibtex..." | tee -a "$LOGFILE"
bibtex main >> "$LOGFILE" 2>&1

# ── Step 3: pdflatex pass 2 ──────────────────────────────────────────────────
echo "[3/4] Running pdflatex (pass 2)..." | tee -a "$LOGFILE"
pdflatex -interaction=nonstopmode main.tex >> "$LOGFILE" 2>&1

# ── Step 4: pdflatex pass 3 ──────────────────────────────────────────────────
echo "[4/4] Running pdflatex (pass 3)..." | tee -a "$LOGFILE"
pdflatex -interaction=nonstopmode main.tex >> "$LOGFILE" 2>&1

# ── Results ──────────────────────────────────────────────────────────────────
if [ -f main.pdf ]; then
    PAGES=$(pdfinfo main.pdf 2>/dev/null | grep Pages | awk '{print $2}')
    SIZE=$(ls -lh main.pdf | awk '{print $5}')
    echo "---" | tee -a "$LOGFILE"
    echo "✓ Build successful!" | tee -a "$LOGFILE"
    echo "  PDF: main.pdf" | tee -a "$LOGFILE"
    echo "  Pages: $PAGES" | tee -a "$LOGFILE"
    echo "  Size: $SIZE" | tee -a "$LOGFILE"
    echo "  Log: $LOGFILE" | tee -a "$LOGFILE"

    WARNINGS=$(grep -c "Warning" "$LOGFILE")
    ERRORS=$(grep -c "^!" "$LOGFILE")
    echo "  Warnings: $WARNINGS" | tee -a "$LOGFILE"
    echo "  Errors: $ERRORS" | tee -a "$LOGFILE"
else
    echo "✗ Build failed!" | tee -a "$LOGFILE"
    echo "Check log file for details: $LOGFILE" | tee -a "$LOGFILE"
    exit 1
fi

# ── Cleanup ──────────────────────────────────────────────────────────────────
echo "Cleaning build artifacts..."

rm -f main.aux main.bbl main.blg main.log main.out
rm -f main.toc main.lof main.lot
rm -f main.fdb_latexmk main.fls main.synctex.gz

echo "✓ Cleaned!"
