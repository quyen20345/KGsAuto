# Knowledge Graph Extraction Service

## Overview
`services/extraction` là pipeline trích xuất tri thức từ tài liệu Markdown để tạo ra dữ liệu Knowledge Graph chuẩn JSON (`nodes`, `relationships`) bằng LLM.
Module này hỗ trợ chạy batch, retry khi lỗi, validation cấu trúc output, logging và metrics tổng hợp theo từng run.

## Quick Start

```bash
# Từ root project
python -m services.extraction.cli \
  --input-dir data/raw/uet \
  --output-dir data/extracted \
  --provider OpenAICompatible \
  --model cx/gpt-5.3-codex
```

Ví dụ chạy lại toàn bộ file (không skip file đã có output):

```bash
python -m services.extraction.cli --no-skip-existing
```

Các tham số hữu ích:
- `--max-retries`: số lần retry khi lỗi LLM/parse JSON
- `--save-failed` / `--no-save-failed`: lưu raw response lỗi để debug
- `--failed-dir`: thư mục chứa failed responses

## Architecture (detailed architecture diagram)
Kiến trúc extraction gồm 6 lớp chính:
1. **CLI Layer (`cli.py`)**: nhận args, validate input, khởi chạy pipeline.
2. **Config Layer (`config.py`)**: quản lý cấu hình runtime và đường dẫn output/log/summary.
3. **Core Orchestration (`extract.py`)**: điều phối đọc file, gọi LLM, parse, validate, save output.
4. **Prompt Contract (`prompt.py`)**: định nghĩa schema JSON + extraction rules cho LLM.
5. **Validation (`validation.py`)**: kiểm tra cấu trúc KG output (soft validation, warning-based).
6. **Metrics & Observability (`metrics.py`)**: thu thập thống kê batch và ghi summary JSON.

### Component Diagram

```mermaid
flowchart TB
    U[User / Scheduler] --> CLI[cli.py\nargparse entrypoint]

    CLI --> CFG[config.py\nExtractionConfig]
    CFG -->|create dirs, run_id| FS[(File System)]

    CLI --> EXT[extract.py\nKGExtractor]
    CFG --> EXT

    EXT --> PROMPT[prompt.py\nget_extraction_prompt]
    EXT --> LLMF[services.llms.get_llm]
    LLMF --> LLM[(LLM Provider\nOpenAICompatible/gemini/ollama)]

    EXT --> VAL[validation.py\nvalidate_and_log]
    EXT --> MET[metrics.py\nExtractionMetrics]

    EXT -->|read .md| IN[(Input Dir\n*.md)]
    EXT -->|write *_kg.json| OUT[(Output Dir)]
    EXT -->|write failed raw response| FAIL[(Failed Dir)]
    EXT -->|write extraction_<run_id>.log| LOG[(Log File)]
    MET -->|write summary json| SUM[(Summary File)]

    VAL -. warnings .-> LOG
    EXT -. progress .-> LOG
```

### Runtime Sequence Diagram

```mermaid
sequenceDiagram
    participant C as cli.py
    participant G as ExtractionConfig
    participant E as KGExtractor
    participant P as prompt.py
    participant L as LLM Client
    participant V as validation.py
    participant M as ExtractionMetrics
    participant F as FileSystem

    C->>G: Build config from args
    G->>F: Ensure output and failed dirs
    C->>E: Create extractor with config
    E->>L: Initialize LLM client

    C->>E: extract_from_dir()
    E->>F: List markdown input files

    loop for each markdown file
        E->>F: Read markdown content
        E->>P: Build extraction prompt
        P-->>E: Prompt text

        loop retry up to max retries
            E->>L: generate(prompt)
            L-->>E: raw response and token usage
            E->>E: Clean and parse JSON

            alt parse or exception error
                E->>E: Backoff with jitter
                opt final retry failed
                    E->>F: Save failed raw response
                end
            else parsed successfully
                E->>V: validate_and_log(kg_data)
                V-->>E: valid or invalid with warning
                E->>F: Write KG json output
                E->>M: Update counters tokens and time
            end
        end
    end

    E->>M: Compute averages
    E->>F: Write summary json
    E->>F: Finalize logs
```

## Project Structure
```text
services/extraction/
├── cli.py          # CLI entrypoint, parse args, start pipeline
├── config.py       # ExtractionConfig: runtime config + output/log paths
├── extract.py      # KGExtractor: core orchestration and batch processing
├── prompt.py       # Prompt template + JSON schema contract for LLM
├── validation.py   # Output structure validation (nodes/relationships)
├── metrics.py      # Batch metrics aggregation and summary export
└── tests/          # Unit/integration tests for extraction module
```