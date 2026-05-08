# Extraction Service Architecture

## Overview

`services/extraction` turns Markdown documents into Knowledge Graph JSON using an LLM. It exists to create a structured intermediate representation (`nodes` and `relationships`) that can be validated, resolved, imported into Neo4j, and used by downstream RAG systems.

The service is intentionally file-oriented: each Markdown file is treated as one extraction chunk, and each successful chunk produces one `*_kg.json` artifact.

```mermaid
flowchart LR
    InputDocs[Markdown files] --> CLI[CLI]
    CLI --> Config[ExtractionConfig]
    Config --> Extractor[KGExtractor]
    Extractor --> Prompt[Prompt builder]
    Prompt --> LLM[LLM provider]
    LLM --> Parser[JSON parser]
    Parser --> Validator[KG validator]
    Validator --> Output[KG JSON files]
    Extractor --> Metrics[Metrics summary]
    Parser --> Failed[Failed responses]
```

## Key Concepts

### Chunk

A chunk is the extraction unit passed to the LLM. In the current implementation, one Markdown file maps to one chunk, and the chunk ID is the file stem.

### Cluster

A cluster is a group of Markdown files whose filenames share similar tokens. Files in the same cluster are processed sequentially so later files can use context collected from earlier files.

### Core Pack

The core pack is a small global instruction block that encourages stable canonical names, concise aliases, and consistent naming across related UET/ĐHQGHN files.

### Local Context

Local context is a short list of entities previously extracted inside the same cluster. It helps the LLM reuse canonical names and aliases.

### Rolling Summary

The rolling summary is a compact list of recent facts from previous successful extractions in the same cluster.

## Module Architecture

```mermaid
flowchart TB
    subgraph CLILayer["CLI Layer"]
        CLI["cli.py<br/>build_parser / main"]
    end

    subgraph ConfigLayer["Configuration"]
        Config["config.py<br/>ExtractionConfig"]
    end

    subgraph CoreLayer["Core Extraction"]
        Extract["extract.py<br/>KGExtractor"]
        Prompt["prompt.py<br/>get_extraction_prompt"]
        Validation["validation.py<br/>validate_and_log"]
        Metrics["metrics.py<br/>ExtractionMetrics"]
    end

    subgraph ContextLayer["Cluster Context"]
        Clustering["clustering.py<br/>cluster_markdown_files"]
        State["cluster_state.py<br/>ClusterState"]
    end

    subgraph External["External Dependencies"]
        LLM["services.llms.get_llm"]
        FileSystem[(File system)]
    end

    CLI --> Config
    CLI --> Extract
    Config --> Extract
    Extract --> Prompt
    Extract --> Validation
    Extract --> Metrics
    Extract --> Clustering
    Extract --> State
    Extract --> LLM
    Extract --> FileSystem
```

| Module | Responsibility |
|---|---|
| `cli.py` | Parses command-line options, validates the input directory, builds `ExtractionConfig`, and starts extraction. |
| `config.py` | Stores runtime configuration, converts string paths to `Path`, creates output directories, and generates run-specific paths. |
| `extract.py` | Main orchestrator. Reads files, builds context, calls the LLM, parses JSON, validates results, writes outputs, and records metrics. |
| `prompt.py` | Defines entity labels, output JSON schema, extraction rules, and context section assembly. |
| `validation.py` | Performs structural validation for nodes and relationships and logs warnings. |
| `metrics.py` | Tracks file counts, entity counts, token usage, processing time, and summary output. |
| `clustering.py` | Groups files by Jaccard similarity over sanitized filename tokens. |
| `cluster_state.py` | Stores extracted entity records and facts for cluster-local context. |

## Runtime Sequence

```mermaid
sequenceDiagram
    autonumber

    participant User
    participant CLI as cli.py
    participant Config as ExtractionConfig
    participant Extractor as KGExtractor
    participant Clusterer as cluster_markdown_files
    participant State as ClusterState
    participant Prompt as prompt.py
    participant LLM as LLM Provider
    participant Validator as validation.py
    participant Metrics as ExtractionMetrics
    participant FS as File System

    User->>CLI: python -m services.extraction.cli
    CLI->>Config: Build config from args
    Config->>FS: Create output and failed dirs
    CLI->>Extractor: KGExtractor(config)
    Extractor->>LLM: get_llm(provider, model_name)

    CLI->>Extractor: extract_from_dir()
    Extractor->>FS: Find input_dir/**/*.md
    Extractor->>Clusterer: Group Markdown files
    Clusterer-->>Extractor: clusters

    loop Each cluster
        Extractor->>State: Create cluster state
        loop Each Markdown file
            Extractor->>FS: Read file content
            Extractor->>State: Build local context and rolling summary
            Extractor->>Prompt: get_extraction_prompt(...)
            Prompt-->>Extractor: Prompt text
            Extractor->>LLM: generate(prompt)
            LLM-->>Extractor: Raw response + metadata
            Extractor->>Extractor: Clean code fences / think tags
            Extractor->>Extractor: json.loads(cleaned_content)
            Extractor->>Validator: validate_and_log(kg_data)

            alt Extraction result returned
                Extractor->>FS: Write *_kg.json
                Extractor->>State: add_result(result)
                Extractor->>Metrics: Increment success counters
            else Parse/API failure after retries
                Extractor->>FS: Save failed response when enabled
                Extractor->>Metrics: Increment failed counters
            end
        end
    end

    Extractor->>Metrics: save_to_file(summary_path)
    Metrics->>FS: Write extraction_summary_<run_id>.json
```

## Processing Flow

```mermaid
flowchart TD
    Start[Start extraction run] --> Discover[Discover Markdown files]
    Discover --> Empty{Any files?}
    Empty -->|No| SaveEmpty[Save empty metrics summary]
    Empty -->|Yes| Cluster[Cluster files by filename similarity]
    Cluster --> Workers{cluster_max_workers > 1?}

    Workers -->|No| Sequential[Process clusters sequentially]
    Workers -->|Yes| Parallel[Process clusters with ThreadPoolExecutor]

    Sequential --> ProcessFile[Process each file]
    Parallel --> ProcessFile

    ProcessFile --> Existing{Output exists and skip_existing?}
    Existing -->|Yes| Skip[Mark skipped]
    Existing -->|No| Read[Read Markdown]
    Read --> Context[Build core pack, local context, rolling summary]
    Context --> Extract[extract_from_text]
    Extract --> Success{Result returned?}
    Success -->|Yes| SaveKG[Write *_kg.json]
    SaveKG --> UpdateState[Update ClusterState]
    UpdateState --> UpdateMetrics[Update success metrics]
    Success -->|No| MarkFailed[Update failed metrics]
    Skip --> Progress[Log progress]
    UpdateMetrics --> Progress
    MarkFailed --> Progress
    Progress --> Done{All files done?}
    Done -->|No| ProcessFile
    Done -->|Yes| Summary[Save summary metrics]
```

## LLM Extraction and Retry Behavior

`KGExtractor.extract_from_text()` is responsible for the LLM call and parse loop. It retries parse/API failures up to `max_retries`.

```mermaid
flowchart TD
    BuildPrompt[Build prompt] --> CallLLM[Call LLM]
    CallLLM --> Raw[Receive raw content]
    Raw --> Clean[Remove JSON code fences and optional think block]
    Clean --> Parse{Valid JSON?}

    Parse -->|No| Attempts{Attempts left?}
    Attempts -->|Yes| Backoff[Sleep with exponential backoff + jitter]
    Backoff --> BuildPrompt
    Attempts -->|No| SaveFailed[Save raw failed response if enabled]
    SaveFailed --> ReturnNone[Return None]

    Parse -->|Yes| Required{Has nodes and relationships?}
    Required -->|No| Error[Raise ValueError]
    Error --> Attempts
    Required -->|Yes| Validate[Validate KG structure]
    Validate --> Valid{Validation valid?}
    Valid -->|Yes| ReturnResult[Return extraction result]
    Valid -->|No, current behavior| Warn[Log warnings but continue]
    Warn --> ReturnResult
```

Important behavior:

- JSON parse failures are retried.
- On the final JSON parse failure, the raw response is saved to `failed_dir` when `save_failed=True`.
- Generic exceptions are retried and eventually return `None`.
- Validation is currently warning-based; invalid structures are logged but still returned as successful extraction results.

## Cluster Context Flow

Clusters allow files with related names to share lightweight context. The first successful file in a cluster populates `ClusterState`; later files receive selected entity records and recent facts in their prompt.

```mermaid
flowchart TB
    Files[Sorted Markdown files] --> Tokenize[Tokenize filename stems]
    Tokenize --> Similarity[Jaccard similarity]
    Similarity --> Clusters[Document clusters]

    subgraph ClusterRun["For each cluster"]
        S0[Empty ClusterState] --> F1[Extract file 1]
        F1 --> S1[Store entity records and facts]
        S1 --> F2[Extract file 2 with local context]
        F2 --> S2[Append new records and facts]
        S2 --> FN[Extract remaining files with rolling context]
    end

    Clusters --> ClusterRun
```

Context sections are capped by `context_char_budget`. When the budget is positive, it is split roughly equally across:

1. core pack,
2. local context,
3. rolling summary.

## Output Data Model

The LLM is instructed to return JSON with two top-level arrays: `nodes` and `relationships`.

```mermaid
classDiagram
    class ExtractionResult {
        string LLM
        string File
        string ProcessingTime
        int NodeCount
        int RelationCount
        Node[] nodes
        Relationship[] relationships
        string chunk_id
        string model
        int usage_tokens
    }

    class Node {
        string id
        string[] labels
        NodeProperties properties
    }

    class NodeProperties {
        string name
        string[] aliases
        string[] chunk_id
        string[] model_extracted
        string[] description
    }

    class Relationship {
        string id
        string type
        string source
        string target
        RelationshipProperties properties
    }

    class RelationshipProperties {
        string[] chunk_id
        string[] model_extracted
        string[] description
    }

    ExtractionResult "1" --> "many" Node
    ExtractionResult "1" --> "many" Relationship
    Node --> NodeProperties
    Relationship --> RelationshipProperties
```

Example output shape:

```json
{
  "LLM": "cx/gpt-5.3-codex",
  "File": "data/raw/uet/example.md",
  "Processing Time": "0:00:12.345678",
  "Node count": 2,
  "Relation count": 1,
  "nodes": [
    {
      "id": "node_university_of_engineering_and_technology",
      "labels": ["UNIVERSITY"],
      "properties": {
        "name": "University of Engineering and Technology",
        "aliases": ["UET"],
        "chunk_id": ["example"],
        "model_extracted": ["cx/gpt-5.3-codex"],
        "description": ["A university-level entity grounded in the source document."]
      }
    }
  ],
  "relationships": [
    {
      "id": "rel_node_university_of_engineering_and_technology_node_vnu_MEMBER_OF",
      "type": "MEMBER_OF",
      "source": "node_university_of_engineering_and_technology",
      "target": "node_vnu",
      "properties": {
        "chunk_id": ["example"],
        "model_extracted": ["cx/gpt-5.3-codex"],
        "description": ["The source text states that UET is a member university of VNU."]
      }
    }
  ],
  "chunk_id": "example",
  "model": "cx/gpt-5.3-codex",
  "usage_tokens": 1234
}
```

> Note: The prompt currently shows list-valued properties for `chunk_id`, `model_extracted`, and `description`, while some natural-language rules say these fields must equal a single value. If downstream consumers require strict typing, align the prompt, validator, and importer expectations before changing the schema.

## Validation Rules

`validation.py` performs structural checks and returns `(is_valid, errors)`.

```mermaid
flowchart TD
    KG[KG data] --> TopLevel{Has nodes and relationships?}
    TopLevel -->|No| Invalid[Invalid]
    TopLevel -->|Yes| NodeLoop[Validate nodes]
    NodeLoop --> NodeID{Each node has id?}
    NodeID -->|No| Invalid
    NodeID --> Labels{labels is non-empty list?}
    Labels -->|No| Invalid
    Labels --> Props{properties is object?}
    Props -->|No| Invalid
    Props --> RequiredProps{Has chunk_id and model_extracted?}
    RequiredProps -->|No| Invalid
    RequiredProps --> UniqueIDs{Node IDs unique?}
    UniqueIDs -->|No| Invalid
    UniqueIDs --> RelLoop[Validate relationships]
    RelLoop --> RelType{Has type?}
    RelType -->|No| Invalid
    RelType --> Endpoints{Source and target exist in nodes?}
    Endpoints -->|No| Invalid
    Endpoints --> Valid[Valid]
```

Current validation is soft:

- invalid outputs produce warnings,
- invalid outputs are still saved as successful extraction results,
- strict rejection would require an additional config or code change.

## Configuration Reference

| CLI flag | Config field | Default | Description |
|---|---|---:|---|
| `--input-dir` | `input_dir` | `data/raw/uet` | Markdown input directory. |
| `--output-dir` | `output_dir` | `data/extracted` | Output directory for KG JSON, logs, and summaries. |
| `--provider` | `provider` | `OpenAICompatible` | LLM provider key passed to `get_llm`. |
| `--model` | `model_name` | `cx/gpt-5.3-codex` | LLM model name. |
| `--max-retries` | `max_retries` | `3` | Retry attempts for each extraction. |
| `--save-failed` / `--no-save-failed` | `save_failed` | `True` | Whether to persist failed raw responses. |
| `--skip-existing` / `--no-skip-existing` | `skip_existing` | `True` | Whether existing `*_kg.json` files are skipped. |
| `--cluster-max-workers` | `cluster_max_workers` | `1` | Number of clusters processed concurrently. |
| `--cluster-similarity-threshold` | `cluster_similarity_threshold` | `0.3` | Jaccard threshold for filename-token clustering. |
| `--failed-dir` | `failed_dir` | `data/failed_responses` | Directory for raw failed responses. |

Additional config fields not currently exposed as CLI flags:

| Config field | Default | Purpose |
|---|---:|---|
| `context_char_budget` | `4000` | Maximum combined context characters before per-section capping. |
| `core_pack_enabled` | `True` | Include global naming guidance. |
| `local_context_enabled` | `True` | Include sampled entity records from the current cluster. |
| `rolling_summary_enabled` | `True` | Include recent facts from the current cluster. |
| `local_context_top_k` | `5` | Number of entity records used for local context. |
| `rolling_summary_max_items` | `20` | Maximum recent facts included in the rolling summary. |
| `random_seed` | `42` | Seed for context shuffling. |
| `progress_log_every` | `10` | Log progress every N processed files. |

## Generated Artifacts

```mermaid
flowchart LR
    Raw[(Input Markdown<br/>data/raw/uet)] --> Extractor[KGExtractor]
    Extractor --> KG[(Extracted KG<br/>data/extracted/*_kg.json)]
    Extractor --> Log[(Run log<br/>data/extracted/extraction_*.log)]
    Extractor --> Summary[(Metrics summary<br/>data/extracted/extraction_summary_*.json)]
    Extractor --> Failed[(Failed raw response<br/>data/failed_responses/*_failed_v2.txt)]
```

| Artifact | Created by | Purpose |
|---|---|---|
| `*_kg.json` | `KGExtractor._process_cluster` | Successful extraction output for one Markdown file. |
| `extraction_<run_id>.log` | `setup_logger` | Console/file log for one extraction run. |
| `extraction_summary_<run_id>.json` | `ExtractionMetrics.save_to_file` | Batch-level counters and averages. |
| `*_failed_v2.txt` | `extract_from_text` | Raw final invalid response after JSON parse retries. |

## Operational Examples

### Normal run

```bash
python -m services.extraction.cli \
  --input-dir data/raw/uet \
  --output-dir data/extracted \
  --provider OpenAICompatible \
  --model cx/gpt-5.3-codex
```

### Re-extract all files

```bash
python -m services.extraction.cli \
  --input-dir data/raw/uet \
  --output-dir data/extracted \
  --no-skip-existing
```

### Debug failed responses

```bash
python -m services.extraction.cli \
  --save-failed \
  --failed-dir data/failed_responses
```

### Process clusters in parallel

```bash
python -m services.extraction.cli \
  --cluster-max-workers 4
```

Use parallel workers carefully. The extractor shares one LLM client instance across worker threads; verify the selected provider/client supports concurrent requests or keep the default `--cluster-max-workers 1`.

## Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| `Input directory does not exist` | Wrong `--input-dir` path. | Check the path relative to the repository root. |
| All files are skipped | Matching `*_kg.json` outputs already exist. | Use `--no-skip-existing` to force re-extraction. |
| JSON parse warnings | LLM returned prose, Markdown, partial JSON, or malformed JSON. | Inspect `data/failed_responses/*_failed_v2.txt`; tighten prompt/model settings if needed. |
| Empty graph warning | Source text has few extractable entities or prompt rules filtered generic mentions. | Inspect the Markdown file and the extraction prompt assumptions. |
| Orphan relationship warning | LLM referenced a node ID that is not present in `nodes`. | Re-run the file or add strict validation before downstream import. |
| Token metrics are zero | Provider response does not include token usage. | Check the selected LLM client implementation. |
| Parallel run is unstable | LLM client or provider rate limits are not concurrency-safe. | Reduce `--cluster-max-workers` to `1`. |

## Known Limitations

1. Validation is warning-based and does not currently block saving invalid graph structures.
2. Filename clustering uses ASCII-oriented tokenization and may be weak for Vietnamese filenames with diacritics.
3. The LLM output contract is prompt-based rather than enforced by a strict Pydantic model.
4. Parallel cluster processing shares one LLM client instance across threads.
5. Some config fields are not exposed through CLI flags.
6. There are currently no dedicated tests under `services/extraction/tests/`.

## Downstream Flow

After extraction, generated `*_kg.json` files are usually passed to entity resolution and then imported into Neo4j.

```mermaid
flowchart LR
    Extraction[Extraction<br/>*_kg.json] --> ER[Entity Resolution<br/>stage1-stage3]
    ER --> FinalGraph[Resolved graph artifacts]
    FinalGraph --> Neo4j[Neo4j import]
    Neo4j --> RAG[RAG graph retrieval]
```

Typical next command:

```bash
python -m services.entity_resolution.cli \
  --stage all \
  --input-dir data/extracted \
  --store-backend memory \
  --run-id demo_run
```
