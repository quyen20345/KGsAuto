# Unified RAG System

## Overview

`services/rag_system` is the runtime retrieval layer behind `apps/rag_api`. It provides one query surface over two evidence stores:

- markdown chunks stored in Qdrant
- entity and relationship data stored in Neo4j

The package exists to let the application answer the same user question through different retrieval strategies without changing the caller. The main entrypoint is `services/rag_system/core/unified_pipeline.py`.

```mermaid
flowchart TB
    User[User question] --> API[apps.rag_api or CLI]
    API --> Pipeline[UnifiedRetrievalPipeline]

    Pipeline --> Semantic[semantic_search]
    Pipeline --> GraphSearch[graph_search]
    Pipeline --> Naive[naive_grag]
    Pipeline --> Hybrid[hybrid]

    Semantic --> Qdrant[(Qdrant markdown chunks)]
    Hybrid --> Qdrant
    Hybrid --> Neo4j[(Neo4j knowledge graph)]
    GraphSearch --> Neo4j
    Naive --> Neo4j

    Semantic --> Synth[AnswerSynthesizer]
    Hybrid --> Synth
    GraphSearch --> DeepReasoning[Deep graph reasoning workflow]
    Naive --> DeepReasoning

    Synth --> Response[RAG response]
    DeepReasoning --> Response
```

## Public modes

`services/rag_system/core/unified_pipeline.py` supports exactly four public modes:

- `semantic_search`: retrieve markdown chunks from Qdrant, then synthesize one answer from text evidence only.
- `graph_search`: run a multi-step Neo4j-only reasoning workflow with decomposition, verification, and optional query expansion.
- `naive_grag`: run a simpler Neo4j-only path that fetches graph context once and answers from it directly.
- `hybrid`: retrieve markdown and graph evidence in parallel, fuse both lists, then synthesize one answer.

## Package structure

```text
services/rag_system/
  cli.py                         # operational CLI
  config.py                      # RAGConfig
  schemas.py                     # Chunk/evidence/response schemas
  README.md
  core/
    unified_pipeline.py          # main orchestration entrypoint
    pipeline.py                  # compatibility alias
  components/
    synthesis.py                 # LLM answer synthesis for semantic/graph/hybrid
    llm/components.py            # async GraphSearch helper calls
    prompts/prompts.py           # GraphSearch prompts
  retrieval/
    markdown.py                  # Qdrant markdown retrieval
    graph.py                     # simple Neo4j fact retrieval
    hybrid.py                    # parallel markdown + graph retrieval and fusion
    indexing.py                  # markdown indexing into Qdrant
    chunking.py                  # markdown chunking strategies
    adapters/
      neo4j_adapter.py           # Neo4j -> GraphSearch context adapter
  storage/
    document.py                  # Qdrant client + embedding upsert/search
    graph.py                     # Neo4j lookup helpers
  workflows/
    deep_graph_search/
      pipeline.py                # graph_search and naive_grag workflows
      parsing.py                 # decomposition/expansion parsing helpers
      utils.py                   # normalization and formatting helpers
  evaluation/
    ragas_eval.py                # dataset generation and comparison runners
    metrics.py                   # benchmark dataclasses/metrics
  tests/
    test_unified_pipeline.py
    test_graph_search_neo4j_adapter.py
    ...
```

## Key concepts

### 1. Two retrieval families

There are two separate retrieval backends:

- **Document retrieval** via `storage/document.py` and `retrieval/markdown.py`
- **Graph retrieval** via `storage/graph.py`, `retrieval/graph.py`, and `retrieval/adapters/neo4j_adapter.py`

### 2. Two graph-only modes

The codebase intentionally keeps two Neo4j-only paths:

- **`naive_grag`** for one-pass context retrieval plus answer generation
- **`graph_search`** for deeper iterative reasoning when the question benefits from decomposition or evidence verification

### 3. Two answer-generation styles

- `semantic_search` and `hybrid` use `components/synthesis.py` and return citation-bearing answers extracted from prompt output.
- `graph_search` and `naive_grag` generate answers inside `workflows/deep_graph_search/pipeline.py` through async workflow components.

## Architecture

### Runtime components

```mermaid
flowchart LR
    subgraph EntryPoints
        CLI[services.rag_system.cli]
        API[apps.rag_api.main]
    end

    subgraph Core
        U[core/unified_pipeline.py]
        S[components/synthesis.py]
    end

    subgraph Retrieval
        MR[retrieval/markdown.py]
        GR[retrieval/graph.py]
        HR[retrieval/hybrid.py]
        NA[retrieval/adapters/neo4j_adapter.py]
    end

    subgraph Storage
        DS[storage/document.py]
        GS[storage/graph.py]
    end

    subgraph Workflow
        WG[workflows/deep_graph_search/pipeline.py]
        LC[components/llm/components.py]
    end

    CLI --> U
    API --> U

    U --> MR
    U --> GR
    U --> HR
    U --> S
    U --> WG

    MR --> DS
    GR --> GS
    HR --> MR
    HR --> GR
    WG --> NA
    WG --> LC
    NA --> GS

    DS --> Q[(Qdrant)]
    GS --> N[(Neo4j)]
```

### Configuration model

`config.py` defines `RAGConfig`, which centralizes:

- data directories (`markdown_dir`, `output_dir`)
- Qdrant settings (`qdrant_url`, `markdown_collection`)
- Neo4j settings (`neo4j_uri`, `neo4j_user`, `neo4j_password`)
- embedding settings (`embedding_model`, `embedding_dim`, `embedding_batch_size`)
- chunking settings (`chunk_strategy`, `max_chunk_size`, `chunk_overlap`)
- retrieval settings (`top_k_markdown`, `top_k_graph`, `max_graph_depth`, `max_relations`)
- LLM settings (`llm_provider`, `llm_model`, `llm_temperature`, `llm_max_tokens`)
- fusion settings for hybrid ranking (`fusion_strategy`, `graph_weight`, `markdown_weight`)
- keyword-extraction settings for the Neo4j GraphSearch adapter
- evaluation dataset/output paths

## How each mode works

### `semantic_search`

`semantic_search` is the simplest path. It retrieves the top-k markdown chunks from Qdrant and asks the synthesizer to answer using only those chunks.

```mermaid
sequenceDiagram
    autonumber
    participant Caller
    participant Pipeline as UnifiedRetrievalPipeline
    participant Retriever as MarkdownRetriever
    participant Store as DocumentStore
    participant Synth as AnswerSynthesizer
    participant Qdrant

    Caller->>Pipeline: query(question, mode=semantic_search)
    Pipeline->>Retriever: retrieve(question, top_k)
    Retriever->>Store: search(question)
    Store->>Qdrant: vector search
    Qdrant-->>Store: chunk payloads + scores
    Store-->>Retriever: markdown chunks
    Retriever-->>Pipeline: markdown chunks
    Pipeline->>Synth: synthesize_markdown_only(question, chunks)
    Synth-->>Pipeline: answer + citations + metadata
    Pipeline-->>Caller: response with markdown evidence
```

Relevant files:
- `services/rag_system/core/unified_pipeline.py:163`
- `services/rag_system/retrieval/markdown.py:7`
- `services/rag_system/storage/document.py:11`
- `services/rag_system/components/synthesis.py:127`

### `naive_grag`

`naive_grag` uses the GraphSearch adapter but skips the full iterative reasoning chain. It fetches formatted graph/document context once, then generates an answer from that context.

```mermaid
sequenceDiagram
    autonumber
    participant Caller
    participant Pipeline as UnifiedRetrievalPipeline
    participant Workflow as naive_grag_reasoning
    participant Adapter as Neo4jAdapter
    participant Neo4j
    participant LLM as GraphSearch LLM helpers

    Caller->>Pipeline: query(question, mode=naive_grag)
    Pipeline->>Workflow: naive_grag_reasoning(question, adapter)
    Workflow->>Adapter: aquery_context(question)
    Adapter->>Neo4j: entity/relationship lookups
    Neo4j-->>Adapter: graph records
    Adapter-->>Workflow: formatted context
    Workflow->>Adapter: aquery_answer(question)
    Adapter->>LLM: answer from formatted context
    LLM-->>Adapter: answer text
    Adapter-->>Workflow: answer
    Workflow-->>Pipeline: answer + context + timings
    Pipeline-->>Caller: response with graph_context
```

Relevant files:
- `services/rag_system/core/unified_pipeline.py:217`
- `services/rag_system/workflows/deep_graph_search/pipeline.py:69`
- `services/rag_system/retrieval/adapters/neo4j_adapter.py:105`

### `graph_search`

`graph_search` is the deepest reasoning path. It starts with initial context retrieval, then builds separate semantic and relational reasoning chains, verifies them, optionally expands queries, and finally produces one final answer.

```mermaid
flowchart TB
    A[Question] --> B[Initial Neo4jAdapter context retrieval]
    B --> C[Initial text summary]
    B --> D[Initial KG summary]

    A --> E[Semantic decomposition]
    A --> F[Relational decomposition]

    E --> G[Semantic subqueries]
    F --> H[Relational subqueries]

    G --> I[Retrieve semantic context]
    I --> J[Summarize semantic context]
    J --> K[Draft semantic intermediate answers]
    K --> L[Verify semantic evidence]
    L -->|insufficient| M[Expand semantic queries]

    H --> N[Retrieve relational context]
    N --> O[Summarize relational context]
    O --> P[Draft relational intermediate answers]
    P --> Q[Verify relational evidence]
    Q -->|insufficient| R[Expand relational queries]

    C --> S[Combine reasoning history]
    D --> S
    J --> S
    O --> S
    M --> S
    R --> S
    S --> T[Final answer generation]
```

Relevant files:
- `services/rag_system/core/unified_pipeline.py:186`
- `services/rag_system/workflows/deep_graph_search/pipeline.py:90`
- `services/rag_system/workflows/deep_graph_search/parsing.py`
- `services/rag_system/components/llm/components.py`

### `hybrid`

`hybrid` runs markdown retrieval and graph retrieval concurrently in a `ThreadPoolExecutor`, deduplicates both result sets, ranks merged items, and then synthesizes one answer across both evidence types.

```mermaid
sequenceDiagram
    autonumber
    participant Caller
    participant Pipeline as UnifiedRetrievalPipeline
    participant Hybrid as HybridRetriever
    participant Markdown as MarkdownRetriever
    participant Graph as GraphRetriever
    participant Synth as AnswerSynthesizer

    Caller->>Pipeline: query(question, mode=hybrid)
    Pipeline->>Hybrid: retrieve(question, top_k_markdown, top_k_graph)
    par Parallel retrieval
        Hybrid->>Markdown: retrieve(question)
        and
        Hybrid->>Graph: retrieve(question)
    end
    Markdown-->>Hybrid: markdown chunks
    Graph-->>Hybrid: graph facts
    Hybrid->>Hybrid: deduplicate + rank merged items
    Hybrid-->>Pipeline: markdown_chunks + graph_facts + merged_context
    Pipeline->>Synth: synthesize_hybrid(question, markdown_chunks, graph_facts)
    Synth-->>Pipeline: answer + citations
    Pipeline-->>Caller: response with both evidence lists
```

Relevant files:
- `services/rag_system/core/unified_pipeline.py:247`
- `services/rag_system/retrieval/hybrid.py:21`
- `services/rag_system/retrieval/graph.py:7`
- `services/rag_system/components/synthesis.py:188`

## Data flow for markdown indexing

The indexing side is separate from query execution. It turns local markdown files into chunk payloads, embeds them with `SentenceTransformer`, and stores them in Qdrant.

```mermaid
flowchart LR
    Files[data/raw/uet/*.md] --> Chunker[MarkdownChunker]
    Chunker --> Payloads[Chunk payloads]
    Payloads --> Embedder[SentenceTransformer]
    Embedder --> Upsert[DocumentStore.upsert_chunks]
    Upsert --> Qdrant[(Qdrant collection)]
```

Relevant files:
- `services/rag_system/retrieval/indexing.py:11`
- `services/rag_system/retrieval/chunking.py:9`
- `services/rag_system/storage/document.py:11`

## Data model

`schemas.py` contains the core runtime types.

```mermaid
classDiagram
    class Chunk {
        +chunk_id: str
        +doc_id: str
        +source_path: str
        +title: str
        +section: str
        +text: str
        +metadata: dict
        +char_start: int
        +char_end: int
        +chunk_index: int
    }

    class MarkdownEvidence {
        +chunk_id: str
        +doc_id: str
        +text: str
        +score: float
        +source_path: str
        +title: str
        +section: str
        +metadata: dict
    }

    class GraphEvidence {
        +entity_id: str
        +entity_name: str
        +fact_type: property|relation|path
        +fact_text: str
        +score: float
        +cypher_query: str
        +metadata: dict
    }

    class RetrievalResult {
        +question: str
        +mode: str
        +markdown_evidence: list
        +graph_evidence: list
        +resolved_entities: list
        +intent: str
        +retrieval_time_ms: float
    }

    class Answer {
        +text: str
        +citations: list
        +confidence: float
        +metadata: dict
    }

    class RAGResponse {
        +question: str
        +answer: str
        +mode: str
        +evidence: RetrievalResult
        +citations: list
        +confidence: float
        +synthesis_time_ms: float
        +total_time_ms: float
        +token_usage: int
        +metadata: dict
    }

    RetrievalResult --> MarkdownEvidence
    RetrievalResult --> GraphEvidence
    RAGResponse --> RetrievalResult
```

## CLI reference

The main operational commands are defined in `services/rag_system/cli.py`:

```bash
python -m services.rag_system.cli test-connections
python -m services.rag_system.cli create-collection
python -m services.rag_system.cli delete-collection
python -m services.rag_system.cli index --limit 100
python -m services.rag_system.cli query --question "Hiệu trưởng là ai?" --mode semantic_search --top-k 5 --show-evidence
python -m services.rag_system.cli info

python -m services.rag_system.cli evaluate generate-dataset
python -m services.rag_system.cli evaluate generate-pilot
python -m services.rag_system.cli evaluate run --dataset <jsonl> --output <jsonl>
python -m services.rag_system.cli evaluate run-comparison --dataset <jsonl>
python -m services.rag_system.cli evaluate score --dataset <jsonl> --results <jsonl>
```

## Runtime requirements

### For `semantic_search`
- Qdrant must be reachable.
- The markdown collection must exist.
- Markdown files must already be indexed.

### For `naive_grag` and `graph_search`
- Neo4j must be reachable.
- The imported graph must already exist.

### For `hybrid`
- Both Qdrant markdown indexing and Neo4j graph data must be available.

### For all modes
- LLM access must be configured through `services.llms.get_llm(...)` or the async GraphSearch helpers.

## Testing surface

Current tests cover the main public behavior instead of every implementation detail:

- `services/rag_system/tests/test_unified_pipeline.py` checks mode behavior, evidence normalization, async entrypoints, and hybrid deduplication.
- `services/rag_system/tests/test_graph_search_neo4j_adapter.py` checks GraphSearch context formatting, context splitting, keyword extraction, fallback behavior, and markdown-chunk resolution.
- additional tests cover chunking, indexing, storage, parsing, and evaluation modules.

## Troubleshooting

### No markdown results returned

Check:
- the Qdrant service is running
- the collection exists
- `python -m services.rag_system.cli index` has been run

The markdown retriever explicitly returns an empty list when the collection does not exist.

### Graph modes fail inside an active event loop

`UnifiedRetrievalPipeline.query()` cannot execute async graph workflows when an event loop is already active. In async callers, use `await UnifiedRetrievalPipeline.aquery(...)` instead.

Relevant file:
- `services/rag_system/core/unified_pipeline.py:71`

### Hybrid mode returns weak fused evidence

Check the fusion settings in `RAGConfig`:
- `fusion_strategy`
- `markdown_weight`
- `graph_weight`

`hybrid` currently supports weighted fusion and reciprocal-rank fusion (`rrf`).

### GraphSearch misses obvious UET entity names

The Neo4j adapter applies domain-specific keyword normalization and boosting for UET/hiệu trưởng queries before retrieval. If results still look wrong, inspect:
- `graph_keyword_extraction_mode`
- `graph_keyword_max_terms`
- `graph_keyword_timeout_seconds`

Relevant file:
- `services/rag_system/retrieval/adapters/neo4j_adapter.py:272`

## Source map

Primary files to read first:

- `services/rag_system/core/unified_pipeline.py`
- `services/rag_system/retrieval/hybrid.py`
- `services/rag_system/retrieval/adapters/neo4j_adapter.py`
- `services/rag_system/workflows/deep_graph_search/pipeline.py`
- `services/rag_system/components/synthesis.py`
- `services/rag_system/cli.py`
