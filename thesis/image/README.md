# Thesis Image & Diagram Manifest

## Agent Note

This file governs thesis image and diagram organization only. For thesis-level
writing and engineering rules, see:

- `../AGENTS.md`
- `../THESIS_RULES.md`

## Directory Structure

```
thesis/image/
├── README.md                ← this file (manifest for coding agents)
├── diagrams/                ← Mermaid source files (.mmd)
│   ├── chapter3/            ←   conceptual system architecture diagram
│   ├── chapter4/            ←   extraction, clustering diagrams
│   ├── chapter5/            ←   entity resolution diagrams
│   └── chapter6/            ←   RAG and question-answering diagrams
├── generated/               ← PNG rendered from diagrams/
│   ├── chapter3/            ←   architecture-overview
│   ├── chapter4/            ←   extraction-pipeline, filename-clustering, graph-schema
│   ├── chapter5/            ←   er-pipeline-overview, er-resolution-concept, etc.
│   └── chapter6/            ←   rag-modes-overview, hybrid-rag-fusion, semantic-search-flow, naive-graph-rag-flow, graph-search-flow
└── static/                  ← non-Mermaid images (screenshots, manual)
    ├── entity_resolution.png, kg_output.png, kg_prompt.png, markdown_raw.png
    ├── property-graph.png, rdf-model.png, UET.png
```

## Figure ↔ Source ↔ Command Map

### Chapter 3 — Problem Analysis and System Architecture

| Figure label                    | PNG used by LaTeX                                      | Source .mmd                                             | Render command                                             |
|---------------------------------|--------------------------------------------------------|---------------------------------------------------------|------------------------------------------------------------|
| `fig:architecture-overview`     | `generated/chapter3/architecture-overview.png`         | `diagrams/chapter3/architecture-overview.mmd`           | `mmdc -i <src> -o <png> -w 1400 -H 1000 -b white`         |

### Chapter 4 — Extraction

| Figure label               | PNG used by LaTeX                                   | Source .mmd                                          | Render command                                           |
|----------------------------|-----------------------------------------------------|------------------------------------------------------|----------------------------------------------------------|
| `fig:extraction-pipeline`  | `generated/chapter4/extraction-pipeline.png`        | `diagrams/chapter4/extraction-pipeline.mmd`          | `mmdc -i <src> -o <png> -w 1200 -H 800`                 |
| `fig:filename-clustering`  | `generated/chapter4/filename-clustering.png`        | `diagrams/chapter4/filename-clustering.mmd`          | `mmdc -i <src> -o <png> -w 1600 -H 1100 -b white`       |
| `fig:graph-schema`         | `generated/chapter4/graph-schema.png`               | `diagrams/chapter4/graph-schema.mmd`                 | `mmdc -i <src> -o <png> -w 1200 -H 600`                 |
| `fig:kg-prompt`            | `static/kg_prompt.png`                              | _(static – screenshot)_                              | —                                                        |
| `fig:json-output`          | `static/kg_output.png`                              | _(static – screenshot)_                              | —                                                        |

### Chapter 5 — Entity Resolution

| Figure label                  | PNG used by LaTeX                                      | Source .mmd                                             | Render command                                              |
|-------------------------------|--------------------------------------------------------|---------------------------------------------------------|-------------------------------------------------------------|
| `fig:er-pipeline-overview`    | `generated/chapter5/er-pipeline-overview.png`          | `diagrams/chapter5/er-pipeline-overview.mmd`           | `mmdc -i <src> -o <png> -w 1400 -H 700 -b white`           |
| `fig:er-resolution-concept`   | `generated/chapter5/er-resolution-concept.png`         | `diagrams/chapter5/er-resolution-concept.mmd`          | `mmdc -i <src> -o <png> -w 1400 -H 800 -b white`           |
| `fig:entity-resolution-example`| `static/entity_resolution.png`                         | _(static – not generated from Mermaid)_                 | —                                                           |

Unused legacy Chapter 5 diagrams (`er-stage1-normalization`, `er-stage2-blocking`,
`er-two-pass-llm`, `er-conservative-fallback`) are kept in the repository for
rollback/reference, but they are intentionally not referenced from the thesis text.

### Chapter 6 — RAG Question Answering

| Figure label                  | PNG used by LaTeX                                  | Source .mmd                                      | Render command                                           |
|-------------------------------|----------------------------------------------------|--------------------------------------------------|----------------------------------------------------------|
| `fig:rag-modes-overview`      | `generated/chapter6/rag-modes-overview.png`        | `diagrams/chapter6/rag-modes-overview.mmd`       | `mmdc -i <src> -o <png> -w 1500 -H 900 -b white`        |
| `fig:hybrid-rag-fusion`       | `generated/chapter6/hybrid-rag-fusion.png`         | `diagrams/chapter6/hybrid-rag-fusion.mmd`        | `mmdc -i <src> -o <png> -w 1400 -H 700 -b white`        |
| `fig:semantic-search-flow`    | `generated/chapter6/semantic-search-flow.png`      | `diagrams/chapter6/semantic-search-flow.mmd`     | `mmdc -i <src> -o <png> -w 1400 -H 500 -b white`        |
| `fig:naive-graph-rag-flow`    | `generated/chapter6/naive-graph-rag-flow.png`      | `diagrams/chapter6/naive-graph-rag-flow.mmd`     | `mmdc -i <src> -o <png> -w 1500 -H 500 -b white`        |
| `fig:graph-search-flow`       | `generated/chapter6/graph-search-flow.png`         | `diagrams/chapter6/graph-search-flow.mmd`        | `mmdc -i <src> -o <png> -w 1800 -H 1100 -b white`       |

### Chapter 2 — Fundamentals

| Figure label         | PNG used by LaTeX              | Source                                  |
|----------------------|--------------------------------|-----------------------------------------|
| `fig:rdf-graph`      | `static/rdf-model.png`         | _(static – not generated from Mermaid)_ |
| `fig:property-graph` | `static/property-graph.png`    | _(static – not generated from Mermaid)_ |

### Cover

| Element          | PNG used by LaTeX     | Source                                  |
|------------------|-----------------------|-----------------------------------------|
| UET logo         | `static/UET.png`      | _(static – not generated from Mermaid)_ |

## How to Work with Diagrams

### Render all diagrams at once

```bash
cd thesis
./scripts/render-diagrams.sh
```

### Render a single diagram

```bash
mmdc \
  -i image/diagrams/chapter5/er-two-pass-llm.mmd \
  -o image/generated/chapter5/er-two-pass-llm.png \
  -w 1400 -H 1000 -b white
```

### Edit a diagram

1. Edit the `.mmd` source file in `diagrams/<chapter>/`
2. Run `./scripts/render-diagrams.sh` to regenerate all PNGs
3. Rebuild thesis: `./build.sh`

### Adding a new diagram

1. Add the `.mmd` source to `diagrams/<chapter>/`
2. Add the render command to `render-diagrams.sh`
3. Add a row to the appropriate chapter table in this `README.md`
4. Render the PNG
5. Add `\includegraphics` in the LaTeX source, referencing `image/generated/<chapter>/<name>.png`
6. Rebuild thesis

## Notes

- **NEVER** edit `.png` files directly — always edit the `.mmd` source and re-render.
- `static/` images have no `.mmd` source; they are screenshots or manually created.
- `graph-schema.mmd` / `graph-schema.png` currently have no LaTeX reference; they are kept for potential future use.
- Some subgraph/diamond labels use double-quote wrapping (`["label with (parens)"]`) to avoid Mermaid CLI parse errors.
- All `mmdc` commands use `-b white` for a white background.
