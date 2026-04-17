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
