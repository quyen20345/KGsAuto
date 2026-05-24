# Services Architecture

## Overview

`services/` contains the backend data pipeline and runtime retrieval layer for KGsAuto. It turns crawled web pages into Markdown, extracts knowledge graph JSON with LLMs, resolves duplicate entities, imports the graph into Neo4j, and serves multiple RAG modes over Neo4j and Qdrant.

```mermaid
flowchart LR
    Web[Web Sources] --> Crawler[crawler]
    Crawler --> Markdown[Markdown Documents]

    Markdown --> Extraction[extraction]
    Extraction --> RawKG[Raw KG JSON]

    RawKG --> ER[entity_resolution]
    ER --> ResolvedKG[Resolved KG JSON]

    ResolvedKG --> Import[neo4j_import]
    Import --> Neo4j[(Neo4j Knowledge Graph)]

    Markdown --> Indexing[rag_system indexing]
    Indexing --> Qdrant[(Qdrant Markdown Chunks)]

    Neo4j --> RAG[rag_system]
    Qdrant --> RAG
    RAG --> ChatAPI[apps/chat_api + CLI]

    Neo4j --> Eval[triplet_evaluation]
    LLMs[llms] --> Extraction
    LLMs --> ER
    LLMs --> RAG
    LLMs --> Eval
```

## Service Responsibilities

| Service | Responsibility | Main entry points |
|---|---|---|
| `crawler` | Crawls source websites and converts pages into cleaned Markdown. | `services/crawler/main.py`, `crawl_lib.py` |
| `extraction` | Extracts nodes and relationships from Markdown into KG JSON using an LLM. | `services/extraction/cli.py`, `extract.py` |
| `entity_resolution` | Deduplicates extracted graph entities and rewrites graph JSON to canonical IDs. | `services/entity_resolution/cli.py`, `pipeline.py` |
| `neo4j_import` | Imports resolved KG JSON into Neo4j. | `services/neo4j_import/import_to_neo4j.py` |
| `rag_system` | Runs semantic, graph, hybrid, naive, and direct RAG modes over Qdrant/Neo4j. | `services/rag_system/cli.py`, `pipeline.py` |
| `triplet_evaluation` | Samples Neo4j relationships and judges KG quality with evidence plus LLM. | `services/triplet_evaluation/cli.py`, `evaluator.py` |
| `llms` | Shared LLM provider abstraction used by extraction, RAG, ER, and evaluation. | `services/llms/factory.py`, `base.py` |
| `config.py` | Shared environment-driven settings for databases, embeddings, LLMs, RAG, and evaluation. | `services/config.py` |

## End-to-End Data Flow

```mermaid
sequenceDiagram
    autonumber
    participant Web as Web Sources
    participant Crawler as services.crawler
    participant Extract as services.extraction
    participant LLM as services.llms
    participant ER as services.entity_resolution
    participant Import as services.neo4j_import
    participant Neo4j
    participant Qdrant
    participant RAG as services.rag_system
    participant Eval as services.triplet_evaluation

    Web->>Crawler: Fetch pages
    Crawler-->>Crawler: Convert HTML to Markdown
    Crawler-->>Extract: Markdown files

    Extract->>LLM: Prompt for nodes/relationships
    LLM-->>Extract: KG JSON response
    Extract-->>ER: Raw *_kg.json files

    ER->>ER: Normalize, embed, cluster, resolve
    ER-->>Import: Canonical rewritten KG JSON

    Import->>Neo4j: Merge nodes and relationships
    Extract-->>Qdrant: Markdown chunks indexed by RAG indexing flow

    RAG->>Qdrant: Semantic markdown retrieval
    RAG->>Neo4j: Graph retrieval / GraphSearch
    RAG->>LLM: Answer synthesis

    Eval->>Neo4j: Sample triplets and collect evidence
    Eval->>LLM: Judge support / contradiction / insufficiency
```

## Key Concepts

### Markdown is the shared source artifact

The crawler produces Markdown, and that Markdown feeds two downstream paths:

```mermaid
flowchart TB
    Markdown[Markdown files]

    Markdown --> Extraction[KG extraction]
    Extraction --> KGJSON[KG JSON]
    KGJSON --> EntityResolution[Entity resolution]
    EntityResolution --> Neo4j[(Neo4j)]

    Markdown --> Chunking[Markdown chunking]
    Chunking --> Qdrant[(Qdrant)]

    Neo4j --> RAG[RAG answers]
    Qdrant --> RAG
```

This split lets the system answer from both textual evidence and graph-structured evidence.

### KG construction is staged

The graph build path is intentionally separated into extraction, resolution, and import.

```mermaid
flowchart LR
    A[Markdown] --> B[Extract noisy local graph]
    B --> C[Resolve duplicate entities]
    C --> D[Rewrite graph with canonical IDs]
    D --> E[Import into Neo4j]

    B -. artifacts .-> B1[Raw nodes/relationships]
    C -. artifacts .-> C1[Cluster assignments]
    C -. artifacts .-> C2[Canonical decisions]
    C -. artifacts .-> C3[ID remap + rewire audit]
```

This makes it easier to inspect quality problems at each boundary instead of debugging only the final Neo4j graph.

### Runtime RAG has multiple modes behind one pipeline

`services/rag_system/pipeline.py` exposes one query surface, while mode modules choose the retrieval strategy.

```mermaid
flowchart TB
    Caller[Chat API or CLI] --> Pipeline[UnifiedRetrievalPipeline]

    Pipeline --> Semantic[semantic_search]
    Pipeline --> Graph[graph_search]
    Pipeline --> Naive[naive_grag]
    Pipeline --> Hybrid[hybrid]
    Pipeline --> Direct[direct]

    Semantic --> Qdrant[(Qdrant)]
    Hybrid --> Qdrant
    Hybrid --> Neo4j[(Neo4j)]
    Graph --> Neo4j
    Naive --> Neo4j

    Semantic --> Synth[AnswerSynthesizer]
    Hybrid --> Synth
    Direct --> LLM[LLM]
    Graph --> GraphWorkflow[GraphSearch workflow]
    Naive --> GraphWorkflow

    Synth --> Response[RAG response]
    LLM --> Response
    GraphWorkflow --> Response
```

## Service Details

### `services/crawler`

The crawler is the ingestion edge. It fetches pages, extracts useful content from HTML, converts structures such as tables, lists, and headings into Markdown, and writes cleaned `.md` files for downstream processing.

Primary files:

- `services/crawler/main.py`
- `services/crawler/crawl_lib.py`
- `services/crawler/crawlv2.py`
- `services/crawler/test_conversion.py`

### `services/extraction`

The extraction service converts Markdown documents into structured KG JSON.

It:

1. Reads Markdown input files.
2. Groups related files into clusters.
3. Builds extraction prompts with optional context.
4. Calls an LLM through `services.llms.get_llm`.
5. Parses and validates JSON.
6. Writes one `*_kg.json` file per source document.
7. Records metrics, logs, and failed raw responses.

```mermaid
flowchart LR
    Input[Markdown files] --> CLI[cli.py]
    CLI --> Config[ExtractionConfig]
    Config --> Extractor[KGExtractor]

    Extractor --> Cluster[clustering.py]
    Extractor --> Prompt[prompt.py]
    Prompt --> LLM[services.llms]
    LLM --> Validation[validation.py]
    Validation --> Output[KG JSON]
    Extractor --> Metrics[metrics.py]
```

Primary files:

- `services/extraction/cli.py`
- `services/extraction/extract.py`
- `services/extraction/config.py`
- `services/extraction/prompt.py`
- `services/extraction/validation.py`
- `services/extraction/clustering.py`
- `services/extraction/cluster_state.py`

### `services/entity_resolution`

Entity resolution deduplicates noisy extracted entities before graph import. It is split into three stages:

```mermaid
flowchart TB
    RawKG[Raw KG JSON files] --> S1[Stage 1<br/>Load, normalize, represent, embed]
    S1 --> Store[(Memory or Qdrant vector store)]

    Store --> S2[Stage 2<br/>Blocking and candidate clustering]
    S2 --> Assignments[cluster_assignments.json]

    Assignments --> S3[Stage 3<br/>Canonical resolution and rewiring]
    Store --> S3

    S3 --> ResolvedKG[Resolved KG JSON]
    S3 --> Audit[Canonical decisions, ID remap, rewire audit]
```

The design separates recall from precision:

- Stage 2 groups plausible duplicates.
- Stage 3 decides what actually merges and rewrites relationships.

Primary files:

- `services/entity_resolution/cli.py`
- `services/entity_resolution/pipeline.py`
- `services/entity_resolution/config.py`
- `services/entity_resolution/types.py`
- `services/entity_resolution/pipelines/stage1_pipeline.py`
- `services/entity_resolution/pipelines/stage2_pipeline.py`
- `services/entity_resolution/pipelines/stage3_pipeline.py`
- `services/entity_resolution/merging/rewire.py`

### `services/neo4j_import`

The import service loads resolved graph JSON into Neo4j.

It is responsible for:

- Creating useful search indexes.
- Merging nodes by primary label and ID.
- Merging relationships by `(source, target, type)`.
- Preserving and enriching searchable properties.

```mermaid
flowchart LR
    ResolvedKG[Resolved KG JSON] --> Importer[KGImporter]
    Importer --> Nodes[import_nodes]
    Importer --> Relationships[import_relationships]
    Nodes --> Neo4j[(Neo4j)]
    Relationships --> Neo4j
```

Primary file:

- `services/neo4j_import/import_to_neo4j.py`

### `services/rag_system`

`rag_system` is the runtime query layer used by the chat API and CLI. It combines two evidence stores:

- Qdrant for Markdown chunks.
- Neo4j for entities and relationships.

```mermaid
flowchart LR
    subgraph Entry
        CLI[services.rag_system.cli]
        API[apps.chat_api]
    end

    subgraph Core
        Pipeline[pipeline.py]
        Modes[modes/*.py]
        Synth[synthesis.py]
    end

    subgraph MarkdownRetrieval
        Retriever[retrieval/retriever.py]
        Store[retrieval/store.py]
        Qdrant[(Qdrant)]
    end

    subgraph GraphRetrieval
        Adapter[graph/neo4j_context_adapter.py]
        Workflow[graph/graph_search/pipeline.py]
        Neo4j[(Neo4j)]
    end

    CLI --> Pipeline
    API --> Pipeline
    Pipeline --> Modes
    Modes --> Retriever
    Modes --> Workflow
    Modes --> Synth
    Retriever --> Store
    Store --> Qdrant
    Workflow --> Adapter
    Adapter --> Neo4j
```

Primary files:

- `services/rag_system/pipeline.py`
- `services/rag_system/config.py`
- `services/rag_system/schemas.py`
- `services/rag_system/synthesis.py`
- `services/rag_system/modes/*.py`
- `services/rag_system/retrieval/*.py`
- `services/rag_system/graph/graph_search/*.py`

### `services/triplet_evaluation`

Triplet evaluation measures graph quality after Neo4j import. It samples graph relationships, gathers local evidence, asks an LLM judge whether each triplet is supported, contradicted, or insufficiently supported, and writes aggregate metrics.

```mermaid
flowchart LR
    Neo4j[(Neo4j)] --> Sampler[sampler.py]
    Sampler --> Evidence[evidence.py]
    Evidence --> Input[input_builder.py]
    Input --> Judge[judge.py]
    Judge --> Writer[writer.py]
    Writer --> Aggregator[aggregator.py]
    Aggregator --> Metrics[Evaluation metrics]
```

Primary files:

- `services/triplet_evaluation/cli.py`
- `services/triplet_evaluation/evaluator.py`
- `services/triplet_evaluation/sampler.py`
- `services/triplet_evaluation/evidence.py`
- `services/triplet_evaluation/judge.py`
- `services/triplet_evaluation/aggregator.py`

### `services/llms`

`llms` provides a shared provider abstraction so other services can call different LLM backends through one interface.

```mermaid
classDiagram
    class BaseLLM {
        <<abstract>>
        +generate(prompt, system_prompt)
    }

    class LLMResponse {
        +content
        +model
        +usage_tokens
    }

    class Factory {
        +register_llm(name)
        +get_llm(provider, model_name)
    }

    class OpenAICompatibleClient
    class GeminiClient
    class OllamaClient

    BaseLLM <|-- OpenAICompatibleClient
    BaseLLM <|-- GeminiClient
    BaseLLM <|-- OllamaClient
    Factory --> BaseLLM
    BaseLLM --> LLMResponse
```

Primary files:

- `services/llms/base.py`
- `services/llms/factory.py`
- `services/llms/types.py`
- `services/llms/clients/*`

## Operational Flow

A typical full run looks like:

```bash
# 1. Crawl or prepare Markdown
python -m services.crawler.main

# 2. Extract raw KG JSON
python -m services.extraction.cli \
  --input-dir data/raw/uet \
  --output-dir data/extracted

# 3. Resolve duplicate entities
python -m services.entity_resolution.cli \
  --stage all \
  --input-dir data/extracted \
  --store-backend memory \
  --run-id demo_run

# 4. Import resolved graph into Neo4j
python -m services.neo4j_import.import_to_neo4j

# 5. Query through RAG
python -m services.rag_system.cli

# 6. Evaluate graph triplets
python -m services.triplet_evaluation.cli
```

Exact arguments may vary by local config and environment variables.

## Configuration

Configuration is split between shared settings and service-specific config modules:

```mermaid
flowchart TB
    Env[Environment variables] --> Shared[services/config.py]

    Shared --> ExtractionConfig[services/extraction/config.py]
    Shared --> ERConfig[services/entity_resolution/config.py]
    Shared --> RAGConfig[services/rag_system/config.py]

    Shared --> Neo4j[Neo4j settings]
    Shared --> Qdrant[Qdrant settings]
    Shared --> LLM[LLM settings]
    Shared --> Embeddings[Embedding settings]
```

Important configuration areas:

- Neo4j URI/user/password.
- Qdrant URL and collection names.
- LLM provider/model/temperature/max tokens.
- Embedding model/dimension/batch size.
- RAG chunking and retrieval limits.
- Evaluation input/output paths.

## Mental Model

The system has two major phases:

1. **Build-time KG pipeline**
   - Crawl -> Markdown -> Extract KG -> Resolve entities -> Import Neo4j.

2. **Runtime answer/evaluation pipeline**
   - RAG queries Neo4j and/or Qdrant.
   - Triplet evaluation samples Neo4j and judges KG quality.

The shared `llms` module supports both phases, while Neo4j and Qdrant are the durable stores that connect offline processing to online retrieval.
