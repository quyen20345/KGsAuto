# Thesis Agent Rules

This folder contains thesis writing, figures, diagrams, scripts, and build
artifacts.

Read and follow:

- `THESIS_RULES.md` for the full anti-over-engineering principles.
- `image/README.md` when working with thesis figures or diagrams.

## Core principle

The thesis is a research artifact, not a production platform.

Optimize for:

- clarity,
- reproducibility,
- explainability,
- evaluation value.

Avoid:

- unnecessary abstractions,
- production-hardening,
- generic frameworks,
- speculative extensibility,
- verbose implementation details that do not support the thesis argument.

## Writing rules

When editing `.tex` files:

- Prioritize methodology, design rationale, tradeoffs, limitations, and evaluation.
- Explain why a component exists before explaining how it works.
- Keep low-level commands, file paths, and setup details out of the main text unless necessary.
- Prefer conceptual descriptions and diagrams over implementation logs.
- Do not add claims that are not supported by the implemented system.
- Keep chapter transitions consistent: extraction → Entity Resolution → RAG/evaluation.

## Diagram rules

When editing figures:

- Mermaid source files live in `image/diagrams/<chapter>/`.
- Generated PNG files live in `image/generated/<chapter>/`.
- Static images live in `image/static/`.
- Never edit generated PNGs directly; edit source diagrams and re-render.
- Keep thesis diagrams conceptual and readable.
- Update `image/README.md` when adding, moving, or renaming figures.

## Coding/script rules

When editing thesis scripts:

- Keep scripts simple, deterministic, and easy to inspect.
- Avoid adding dependencies unless they clearly improve reproducibility.
- Prefer explicit commands over hidden abstractions.
- Run `./build.sh` after changes to `.tex` files or figure paths.
- Run `./scripts/render-diagrams.sh` after changing Mermaid sources.

## Decision heuristic

Before adding a section, figure, dependency, script, or abstraction, ask:

1. Does it support the thesis contribution?
2. Is it necessary for evaluation or reproducibility?
3. Can it be explained clearly in two sentences?
4. Would removing it weaken the thesis?

If the answer is mostly no, leave it out.
