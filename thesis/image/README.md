# Thesis Image Manifest

This directory contains only image assets that are currently used by the thesis, plus the source files needed to regenerate generated figures.

## Current Structure

```text
thesis/image/
├── README.md
├── diagrams/
│   ├── chapter3/architecture-overview.tex
│   ├── chapter4/extraction-pipeline.tex
│   └── chapter5/
│       ├── er-pipeline-overview.tex
│       ├── er-stage1-normalization.tex
│       ├── er-stage2-blocking.tex
│       └── er-resolution-concept.tex
├── generated/
│   ├── chapter3/architecture-overview.png
│   ├── chapter4/extraction-pipeline.png
│   ├── chapter4/kg_prompt.png
│   └── chapter5/
│       ├── er-pipeline-overview.png
│       ├── er-stage1-normalization.png
│       ├── er-stage2-blocking.png
│       └── er-resolution-concept.png
├── human_fallback/
│   ├── entity_view_before_compare.png
│   └── compare.png
└── static/
    ├── UET.png
    ├── raw_graph_visualize.png
    ├── graph_visualize.png
    └── kg_prompt.html
```

## Figure Map

| Thesis item | PNG used by LaTeX | Source |
|---|---|---|
| Cover logo | `static/UET.png` | static image |
| Figure 3.1 | `generated/chapter3/architecture-overview.png` | `diagrams/chapter3/architecture-overview.tex` |
| Chapter 3 graph visualization | `static/raw_graph_visualize.png`, `static/graph_visualize.png` | static screenshots |
| Figure 4.1 | `generated/chapter4/extraction-pipeline.png` | `diagrams/chapter4/extraction-pipeline.tex` |
| Figure 4.x prompt illustration | `generated/chapter4/kg_prompt.png` | `static/kg_prompt.html` |
| Figure 5.1 | `generated/chapter5/er-pipeline-overview.png` | `diagrams/chapter5/er-pipeline-overview.tex` |
| Figure 5.2 | `generated/chapter5/er-stage1-normalization.png` | `diagrams/chapter5/er-stage1-normalization.tex` |
| Figure 5.3 | `generated/chapter5/er-stage2-blocking.png` | `diagrams/chapter5/er-stage2-blocking.tex` |
| Figure 5.4 | `generated/chapter5/er-resolution-concept.png` | `diagrams/chapter5/er-resolution-concept.tex` |
| Human fallback example | `human_fallback/entity_view_before_compare.png`, `human_fallback/compare.png` | static screenshots |

Chapter 6 currently does not use image figures. Its former RAG diagrams were removed to keep the thesis image folder focused on assets used by the current manuscript.

## Regenerating TikZ Figures

Generated TikZ figures can be rebuilt from their `.tex` source with:

```bash
cd thesis/image/diagrams/<chapter>
pdflatex -interaction=nonstopmode -halt-on-error <figure>.tex
pdftoppm -png -r 300 -singlefile <figure>.pdf ../../generated/<chapter>/<figure>
rm -f <figure>.aux <figure>.log <figure>.pdf
```

The main `thesis/build.sh` currently compiles the thesis PDF only; it does not automatically regenerate image assets.
