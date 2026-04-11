# Entity Resolution Pipeline

`entity_resolution` is a 3-stage pipeline for automated entity resolution using LLM-based clustering.

## 1) Overview

Pipeline consists of 3 stages:

1. **Stage 1 - Embedding pipeline**
   - Load JSON graph files (`nodes`, `relationships`)
   - Normalize node properties (`name`, `aliases`, `evidence_text`, ...)
   - Create `embedding_text` representation for each node
   - Generate semantic embeddings (automatic fallback to hash if model fails)
   - Store vectors + metadata in vector store (`memory` / `qdrant`)

2. **Stage 2 - Clustering pipeline**
   - Fetch vectors from store by `run_id`/collection
   - Cluster by `primary_type` using HDBSCAN or cosine threshold
   - Output cluster assignments + HTML dashboard for visualization

3. **Stage 3 - LLM-CER Resolution**
   - Fully automated entity resolution using LLM-based clustering
   - **NRS**: Build optimal record sets
   - **LLM Clustering**: Group entities using LLM
   - **MDG Validation**: Validate clustering quality
   - **CMR Merge**: Hierarchical merge across rounds
   - Generate `id_remap` and rewrite graph output

## 2) Module Structure (Function-Based)

```text
entity_resolution/
├── cli.py                    # Command-line interface
├── config.py                 # Configuration dataclass
├── types.py                  # Type definitions
├── README.md                 # This file
│
├── pipelines/                # ✨ Pipeline orchestration (all stages)
│   ├── stage1_pipeline.py    # Stage 1: Preprocessing & Embedding
│   ├── stage2_pipeline.py    # Stage 2: Clustering
│   └── stage3_pipeline.py    # Stage 3: Resolution & Merging
│
├── preprocessing/            # Data loading & embedding
│   ├── loader.py             # Load JSON graph files
│   ├── normalize.py          # Normalize properties, extract primary_type
│   ├── representation.py     # Build embedding_text, create vectors
│   └── logger.py             # Logging setup
│
├── blocking/                 # Blocking strategies (reduce comparisons)
│   ├── vector_fetch.py       # Fetch vectors from store (type-based blocking)
│   └── record_set_builder.py # NRS algorithm (optimal sampling)
│
├── matching/                 # Similarity matching methods
│   ├── fuzzy_validation.py   # Fuzzy string matching (Levenshtein)
│   └── llm_cer.py            # LLM-based semantic matching
│
├── clustering/               # Clustering algorithms
│   ├── cluster.py            # HDBSCAN / threshold-based clustering
│   └── cluster_merger.py     # CMR hierarchical merge
│
├── merging/                  # Entity merging & graph rewriting
│   ├── merge_engine.py       # ID remapping logic
│   └── rewire.py             # Graph rewriting (merge nodes & rels)
│
├── evaluation/               # Metrics & visualization
│   ├── metrics.py            # Clustering quality metrics
│   ├── mdg_validator.py      # MDG validation (stage 3)
│   ├── review_ui_stage2.py   # Stage 2 cluster dashboard
│   └── review_ui_stage3.py   # Stage 3 resolution dashboard
│
├── storage/                  # Vector store adapters
│   ├── entity_store_adapter.py
│   └── review_store.py
│
└── tests/                    # Unit & integration tests
    ├── stage1/
    ├── stage2/
    └── stage3/
```

### Entity Resolution Pipeline Flow

```
preprocessing → blocking → matching → clustering → merging
     ↓             ↓          ↓           ↓           ↓
                    evaluation ←──────────┴───────────┘
```

**Dependency structure:**
- `preprocessing/`: Independent (only uses config, storage)
- `blocking/`: Imports from preprocessing
- `matching/`: Imports from blocking
- `clustering/`: Imports from matching, blocking
- `merging/`: Imports from clustering, matching, blocking
- `evaluation/`: Imports from clustering, merging
- `pipelines/`: Orchestrates all modules for each stage

## 3) Prerequisites

- Run from repo root: `/home/quyen/Documents/KGsAuto`
- Python environment with required dependencies
- If using `qdrant`: Qdrant server running
- LLM API key (OpenAI, Anthropic, or Proxypal)

## 4) Store Backends

- `memory`: Fast for local testing (data lost between runs)
- `qdrant`: Persistent vectors in Qdrant collection

**Important:**
- `memory` only persists within **1 process**
- For separate stage runs, use `qdrant`
- With `memory`, run `--stage all` in one command

## 5) Running the Pipeline

All commands run from repo root.

### 5.1 Full Pipeline (Recommended)

```bash
python -m services.entity_resolution.cli \
  --stage all \
  --input-dir data/extracted \
  --store-backend memory \
  --run-id demo_all \
  --llm-provider openai \
  --llm-model gpt-4o \
  --llm-api-key $OPENAI_API_KEY
```

### 5.2 Run Stage 1 Only

```bash
python -m services.entity_resolution.cli \
  --stage stage1 \
  --input-dir data/extracted \
  --store-backend qdrant \
  --run-id demo_step
```

Output: `stage1/index.json`

### 5.3 Run Stage 2 Only

```bash
python -m services.entity_resolution.cli \
  --stage stage2 \
  --store-backend qdrant \
  --run-id demo_step \
  --min-cluster-size 2 \
  --min-samples 1 \
  --cluster-threshold 0.72
```

Output:
- `stage2/cluster_assignments.json`
- `stage2/cluster_dashboard.html`

### 5.4 Run Stage 3 Only

```bash
python -m services.entity_resolution.cli \
  --stage stage3 \
  --store-backend qdrant \
  --run-id demo_step \
  --llm-provider openai \
  --llm-model gpt-4o \
  --llm-api-key $OPENAI_API_KEY
```

Output:
- `stage3/synthesis_decisions.json`
- `stage3/id_remap.json`
- `stage3/rewire_audit.json`
- `stage3/review_dashboard.html`
- `stage3/output_graph/*.json`

## 6) LLM Configuration

### Required Parameters:
- `--llm-provider`: `openai`, `anthropic`, or `proxypal`
- `--llm-model`: Model name (e.g., `gpt-4o`, `claude-3-5-sonnet-20241022`)
- `--llm-api-key`: API key (or set via environment variable)

### Optional Parameters:
- `--llm-set-size`: Record set size (default: 9)
- `--mdg-threshold`: MDG validation threshold (default: 0.1)
- `--cmr-threshold`: CMR merge threshold (default: 0.80)

### Environment Variables:
```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...

# Run without --llm-api-key flag
python -m services.entity_resolution.cli \
  --stage all \
  --llm-provider openai \
  --llm-model gpt-4o
```

## 7) Visualize Results

### Stage 2 Dashboard (Clustering)
Open: `services/entity_resolution/artifacts/<run_id>/stage2/cluster_dashboard.html`

Features:
- Filter by `primary_type`
- Search by `node_id`/`name`
- Filter by minimum cluster size
- Show/hide noise

### Stage 3 Dashboard (Resolution)
Open: `services/entity_resolution/artifacts/<run_id>/stage3/review_dashboard.html`

Features:
- View cluster validation results
- View canonical entity synthesis
- Export JSON templates
- Review LLM-CER decisions

## 8) Example with Real Data

```bash
python -m services.entity_resolution.cli \
  --stage all \
  --input-dir data/extracted \
  --store-backend memory \
  --run-id extracted_demo \
  --llm-provider openai \
  --llm-model gpt-4o
```

Then open:
- `services/entity_resolution/artifacts/extracted_demo/stage2/cluster_dashboard.html`
- `services/entity_resolution/artifacts/extracted_demo/stage3/review_dashboard.html`
- `services/entity_resolution/artifacts/extracted_demo/stage3/rewire_audit.json`

## 9) Tests

```bash
# Run all tests
python -m pytest services/entity_resolution/tests/ -v

# Run specific stage tests
python -m pytest services/entity_resolution/tests/stage1 -q
python -m pytest services/entity_resolution/tests/stage2 -q
python -m pytest services/entity_resolution/tests/stage3 -q
```

## 10) Architecture Notes

### Why Function-Based Structure?

The codebase is organized by **Entity Resolution functions** rather than pipeline stages:

- **Easier to understand**: All matching code in `matching/`, all clustering in `clustering/`
- **Easier to test**: Unit test each module independently
- **Easier to maintain**: Clear where to add new algorithms
- **Centralized orchestration**: All pipeline logic in `pipelines/` folder
- **Still supports stage execution**: CLI preserves `--stage stage1/stage2/stage3` interface

### Module Responsibilities

| Module | Responsibility | ER Function |
|--------|---------------|-------------|
| `pipelines/` | Orchestrate stages | Pipeline Coordination |
| `preprocessing/` | Load, normalize, vectorize | Data Preprocessing |
| `blocking/` | Reduce comparison space | Blocking |
| `matching/` | Compute similarity | Matching |
| `clustering/` | Group similar entities | Clustering |
| `merging/` | Create canonical entities | Merging/Fusion |
| `evaluation/` | Metrics & visualization | Evaluation |

### Adding New Features

**Example: Add a new matching method**
1. Create `matching/semantic_matching.py`
2. Implement matching logic
3. Import in `pipelines/stage2_pipeline.py`
4. Add unit tests in `tests/matching/`

**Example: Add a new clustering algorithm**
1. Create `clustering/dbscan.py`
2. Implement clustering logic
3. Update `pipelines/stage2_pipeline.py` to use it
4. Add unit tests in `tests/clustering/`

**Example: Modify pipeline orchestration**
1. Edit `pipelines/stage1_pipeline.py` (or stage2/stage3)
2. All pipeline logic is centralized here
3. No need to search across multiple modules
