# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Scope: **Only this directory** (`extractv2/`). This module performs LLM-based knowledge-graph extraction from markdown into JSON files.

## What this module does

- Reads `*.md` files from an input directory.
- For each file, calls an LLM with a strict prompt/schema.
- Parses the LLM JSON response into a KG payload (`nodes`, `relationships`) and writes `*_kg_v2.json` outputs.
- Retries on failures; optionally persists the last failed raw response to `data/failed_responses/`.

Key entry points:
- `extractv2/extractv2.py`: extraction pipeline + CLI-ish `__main__`
- `extractv2/promptv2.py`: prompt template + schema/rules enforced in extraction

## Common commands

### Run extraction (module entry)

From repo root:

```bash
python3 -m extractv2.extractv2
```

This runs the `__main__` block in `extractv2.py` and (by default) extracts:
- input: `data/raw/uet/*.md`
- output: `data/extracted_v2/*_kg_v2.json`

### Run with custom input/output (recommended)

`extractv2.py` currently hardcodes the call in `__main__`. To run with different dirs without editing code, invoke it in a small one-liner:

```bash
python3 -c "from extractv2.extractv2 import KGExtractorV2; KGExtractorV2(provider='proxypal', model_name='gpt-5').extract_from_dir(input_dir='data/raw/uet', output_dir='data/extracted_v2')"
```

### Install dependencies (repo-level)

This module imports `llms.get_llm` from the repo; install repo deps first:

```bash
pip install -r requirements.txt
```

## Architecture (big picture)

### 1) Extractor orchestration (`extractv2.py`)

Core class: `KGExtractorV2`.

Flow (per document):
1. Read markdown file content.
2. Build an extraction prompt via `get_extraction_prompt(text, doc_id, model_name)`.
3. Call LLM: `self.llm.generate(prompt)`.
4. Clean response text (strip ```json fences; drop `<think>...</think>` if present).
5. `json.loads(...)` into a dict.
6. Validate presence of `nodes` and `relationships`.
7. Write output JSON to `{output_dir}/{stem}_kg_v2.json`.

Retries:
- Retries up to `max_retries` with exponential backoff (`time.sleep(2 ** attempt)`).
- On final JSON parse failure, writes a raw dump to `data/failed_responses/{doc_id}_failed_v2.txt`.

Outputs include both KG content and run metadata:
- `nodes`, `relationships`
- `doc_id`
- model/usage info returned by the LLM client (`response.model`, `response.usage_tokens`)

### 2) Prompt + schema contract (`promptv2.py`)

`promptv2.py` defines a strict JSON contract and extraction rules:
- Output must be JSON with:
  - `nodes[]`: `id`, single `labels[]`, `properties{...}`
  - `relationships[]`: `id`, `type`, `source`, `target`, `properties{...}`
- Allowed entity labels are enumerated in `OBJECTS`.
- Allowed relationship types are enumerated in `RELATIONSHIP_TYPES`.
- Strong constraints:
  - **one label per node**
  - **no nested objects** in properties (only primitives/arrays/null)
  - every node/relationship includes `source_document_id`, `model_extracted`, `evidence_text`
  - relationship endpoints must reference existing node IDs
  - avoid duplicates (node IDs and (source,type,target) edges)

`get_extraction_prompt()` injects runtime values into rules:
- `source_document_id` is set to `doc_id`.
- `model_extracted` is set to `model_name`.

### 3) External dependency boundary

This module depends on the repo-level LLM abstraction:
- `from llms import get_llm`

`get_llm(provider, model_name=...)` returns an object with:
- `generate(prompt)` → response with `.content`, `.model`, `.usage_tokens`

When debugging failures, focus on:
- provider/model configuration passed to `KGExtractorV2`
- whether the provider returns fenced JSON, extra text, or `<think>` blocks

## Key conventions

- Input directory expects markdown: `*.md`.
- Output files: `{stem}_kg_v2.json`.
- Failed raw responses: `data/failed_responses/`.

## Quick troubleshooting

- **JSONDecodeError**: check `data/failed_responses/*_failed_v2.txt` to see the raw LLM output.
- **Missing nodes/relationships**: the model violated the schema; adjust prompt rules in `promptv2.py`.
- **Re-running extraction**: existing output files are skipped (idempotent behavior per file).