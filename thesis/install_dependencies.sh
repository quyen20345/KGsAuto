#!/bin/bash
# Install LaTeX dependencies for thesis compilation
# Run this script on a new machine to install all required packages

set -e  # Exit on error

echo "=========================================="
echo "Installing LaTeX Dependencies for Thesis"
echo "=========================================="
echo ""

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "Cannot detect OS. Please install manually."
    exit 1
fi

echo "Detected OS: $OS"
echo ""

# Install based on OS
case $OS in
    ubuntu|debian)
        echo "Installing TeX Live and required packages..."
        sudo apt-get update
        sudo apt-get install -y \
            texlive-base \
            texlive-latex-base \
            texlive-latex-extra \
            texlive-fonts-recommended \
            texlive-fonts-extra \
            texlive-lang-other \
            texlive-science \
            texlive-pictures \
            texlive-bibtex-extra \
            texlive-xetex \
            latexmk \
            poppler-utils

        # Install VnTeX for Vietnamese support
        echo ""
        echo "Installing VnTeX for Vietnamese support..."
        sudo apt-get install -y \
            texlive-lang-other \
            latex-cjk-all
        ;;

    fedora|rhel|centos)
        echo "Installing TeX Live and required packages..."
        sudo dnf install -y \
            texlive-scheme-medium \
            texlive-collection-langother \
            texlive-collection-fontsrecommended \
            texlive-collection-fontsextra \
            texlive-collection-latexextra \
            texlive-collection-science \
            texlive-collection-pictures \
            poppler-utils
        ;;

    arch|manjaro)
        echo "Installing TeX Live and required packages..."
        sudo pacman -S --noconfirm \
            texlive-core \
            texlive-latexextra \
            texlive-fontsextra \
            texlive-langextra \
            texlive-science \
            texlive-pictures \
            texlive-bibtexextra \
            poppler
        ;;

    *)
        echo "Unsupported OS: $OS"
        echo "Please install TeX Live manually from: https://www.tug.org/texlive/"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "Verifying installation..."
echo "=========================================="

# Check if pdflatex is available
if command -v pdflatex &> /dev/null; then
    echo "✓ pdflatex: $(pdflatex --version | head -n1)"
else
    echo "✗ pdflatex not found"
    exit 1
fi

# Check if bibtex is available
if command -v bibtex &> /dev/null; then
    echo "✓ bibtex: $(bibtex --version | head -n1)"
else
    echo "✗ bibtex not found"
    exit 1
fi

# Check if pdfinfo is available
if command -v pdfinfo &> /dev/null; then
    echo "✓ pdfinfo: available"
else
    echo "✗ pdfinfo not found (optional, for page counting)"
fi

echo ""
echo "=========================================="
echo "Required LaTeX Packages (from main.tex):"
echo "=========================================="
echo "✓ titlesec"
echo "✓ indentfirst"
echo "✓ setspace"
echo "✓ geometry"
echo "✓ graphicx"
echo "✓ vietnam (VnTeX)"
echo "✓ times"
echo "✓ tikz"
echo "✓ multido"
echo "✓ booktabs"
echo "✓ amsmath, amssymb, amsfonts, amsthm"
echo "✓ array"
echo "✓ epsfig, epstopdf"
echo "✓ url"
echo "✓ mathrsfs"
echo "✓ etoolbox"
echo "✓ makecell"
echo "✓ float"
echo "✓ xcolor"
echo "✓ listings"
echo "✓ inconsolata"
echo "✓ multirow"
echo "✓ mdframed"
echo "✓ tabularx"
echo "✓ tcolorbox"
echo "✓ fancyvrb"
echo "✓ caption"
echo "✓ hyperref"
echo "✓ enumitem"
echo "✓ fancyhdr"
echo "✓ xpatch"

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "You can now build the thesis by running:"
echo "  cd $(dirname "$0")"
echo "  ./build.sh"
echo ""
