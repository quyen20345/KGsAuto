#!/bin/bash
# Build thesis with logging

# Tạo thư mục logs nếu chưa có
mkdir -p logs

# Tạo tên file log với timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOGFILE="logs/build_${TIMESTAMP}.log"

echo "Building thesis..." | tee "$LOGFILE"
echo "Log file: $LOGFILE" | tee -a "$LOGFILE"
echo "---" | tee -a "$LOGFILE"

# Build với pdflatex
echo "[1/4] Running pdflatex (pass 1)..." | tee -a "$LOGFILE"
pdflatex -interaction=nonstopmode main.tex >> "$LOGFILE" 2>&1

# Build bibliography
echo "[2/4] Running bibtex..." | tee -a "$LOGFILE"
bibtex main >> "$LOGFILE" 2>&1

# Build lần 2
echo "[3/4] Running pdflatex (pass 2)..." | tee -a "$LOGFILE"
pdflatex -interaction=nonstopmode main.tex >> "$LOGFILE" 2>&1

# Build lần 3
echo "[4/4] Running pdflatex (pass 3)..." | tee -a "$LOGFILE"
pdflatex -interaction=nonstopmode main.tex >> "$LOGFILE" 2>&1

# Kiểm tra kết quả
if [ -f main.pdf ]; then
    PAGES=$(pdfinfo main.pdf 2>/dev/null | grep Pages | awk '{print $2}')
    SIZE=$(ls -lh main.pdf | awk '{print $5}')
    echo "---" | tee -a "$LOGFILE"
    echo "✓ Build successful!" | tee -a "$LOGFILE"
    echo "  PDF: main.pdf" | tee -a "$LOGFILE"
    echo "  Pages: $PAGES" | tee -a "$LOGFILE"
    echo "  Size: $SIZE" | tee -a "$LOGFILE"
    echo "  Log: $LOGFILE" | tee -a "$LOGFILE"

    # Kiểm tra warnings
    WARNINGS=$(grep -c "Warning" "$LOGFILE")
    ERRORS=$(grep -c "^!" "$LOGFILE")
    echo "  Warnings: $WARNINGS" | tee -a "$LOGFILE"
    echo "  Errors: $ERRORS" | tee -a "$LOGFILE"
else
    echo "✗ Build failed!" | tee -a "$LOGFILE"
    echo "Check log file for details: $LOGFILE" | tee -a "$LOGFILE"
    exit 1
fi


#!/bin/bash
# Clean build artifacts

echo "Cleaning build artifacts..."

rm -f main.aux
rm -f main.bbl
rm -f main.blg
rm -f main.log
rm -f main.out
rm -f main.toc
rm -f main.lof
rm -f main.lot
rm -f main.fdb_latexmk
rm -f main.fls
rm -f main.synctex.gz

echo "✓ Cleaned!"
