# KGsAuto - Knowledge Graph Automation System

KGsAuto là hệ thống xây dựng Knowledge Graph từ tài liệu tiếng Việt, xử lý trùng lặp entity, lưu graph vào Neo4j, index tài liệu vào Qdrant và cung cấp API/frontend để search, visualize và hỏi đáp chatbot.

## Cài đặt

```bash
pip install -r requirements.txt
pip install -e . --no-deps    # Cài đặt package kgsauto ở chế độ dev, không cài deps từ pyproject
```

Sao chép `.env.example` thành `.env` và điền các biến cần thiết:

- `OPENAI_COMPATIBLE_API_KEY`
- `OPENAI_COMPATIBLE_BASE_URL`
- `OPENAI_COMPATIBLE_MODEL`
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`

## Chạy nhanh các services

Mở 4 terminal tại thư mục gốc repo.

### Terminal 1 - Hạ tầng Docker

```bash
docker compose up -d
```

Lệnh này khởi động:

- Neo4j
- Qdrant
- Ollama

### Terminal 2 - Graph API

```bash
uvicorn apps.graph_api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Terminal 3 - Chat API

```bash
uvicorn apps.chat_api.main:app --host 0.0.0.0 --port 8002 --reload
```

### Terminal 4 - Frontend

```bash
cd apps/frontend && npm install && npm run dev
```

## Các địa chỉ sau khi chạy

- Frontend: http://localhost:5173
- Graph API Docs: http://localhost:8000/docs
- Chat API Docs: http://localhost:8002/docs
- Chat API Health: http://localhost:8002/health
- Neo4j Browser: http://localhost:7474
  - user: `neo4j`
  - password: `12345678`
- Qdrant Dashboard: http://localhost:6333/dashboard
- Ollama API: http://localhost:11434

## Dừng services

Frontend/backend/chat API: nhấn `Ctrl + C` ở terminal đang chạy.

Docker services:

```bash
docker compose down
```

## Chat API

`apps/chat_api` là API chatbot mới, thay thế `apps/rag_api` cũ.

### Endpoints

```text
GET  /health
GET  /modes
POST /query
```

### Query mẫu

```bash
curl -X POST http://localhost:8002/query \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hiệu trưởng là ai?",
    "mode": "semantic_search",
    "top_k": 5,
    "include_evidence": true
  }'
```

### Modes

- `semantic_search`: cần Qdrant running + collection đã tạo + markdown đã index.
- `graph_search`: cần Neo4j running + graph đã import.
- `naive_grag`: cần Neo4j running + graph đã import.
- `hybrid`: cần cả Qdrant markdown index và Neo4j graph.

## Chạy extract knowledge graph

```bash
python -m services.extraction.cli \
  --input-dir data/raw/uet \
  --output-dir data/extracted \
  --provider OpenAICompatible \
  --model cx/gpt-5.3-codex
```

Chạy lại toàn bộ, bỏ qua chế độ skip file đã tồn tại:

```bash
python -m services.extraction.cli \
  --input-dir data/raw/uet \
  --output-dir data/extracted \
  --provider OpenAICompatible \
  --model cx/gpt-5.3-codex \
  --no-skip-existing
```

Xem options:

```bash
python -m services.extraction.cli --help
```

## Chạy entity resolution

### Chạy nhanh toàn bộ 3 stage

```bash
python -m services.entity_resolution.cli \
  --stage all \
  --input-dir data/extracted \
  --store-backend memory \
  --run-id demo_run
```

Lưu ý:

- `memory` nhanh nhưng không lưu dữ liệu giữa các lần chạy.
- Với `memory`, dùng `--stage all` trong một lệnh.

### Chạy từng stage với Qdrant backend

```bash
python -m services.entity_resolution.cli \
  --stage stage1 \
  --input-dir data/extracted \
  --store-backend qdrant \
  --run-id my_run

python -m services.entity_resolution.cli \
  --stage stage2 \
  --store-backend qdrant \
  --run-id my_run

python -m services.entity_resolution.cli \
  --stage stage3 \
  --store-backend qdrant \
  --run-id my_run
```

Options hay dùng:

- `--llm-provider OpenAICompatible`
- `--llm-model cx/gpt-5.3-codex`
- `--enable-llm-blocking`
- `--no-llm-blocking`
- `--cluster-threshold 0.72`

## Import vào Neo4j

Sau khi chạy entity resolution, import graph đã resolve vào Neo4j:

```bash
python -m services.neo4j_import.import_to_neo4j \
  --dir data/entity_resolution/artifacts/final/stage3/output_graph
```

## Index markdown cho RAG/Chat API

```bash
python -m services.rag_system.cli test-connections
python -m services.rag_system.cli create-collection
python -m services.rag_system.cli index --limit 100
```

Test query trực tiếp bằng CLI:

```bash
python -m services.rag_system.cli query \
  --question "Hiệu trưởng là ai?" \
  --mode semantic_search \
  --top-k 5 \
  --show-evidence
```

## Testing

Tests chạy trong conda env `py312`:

```bash
conda run -n py312 python -m pytest apps/chat_api/tests -q
conda run -n py312 python -m pytest apps/graph_api/tests -q
conda run -n py312 python -m pytest services/rag_system/tests -q
conda run -n py312 python -m pytest services/entity_resolution/tests -q
conda run -n py312 python -m pytest services/extraction/tests -v
```

Frontend:

```bash
cd apps/frontend && npm run lint
cd apps/frontend && npm run build
```

## Ghi chú

- Luôn chạy lệnh từ thư mục gốc repo.
- Docker Compose hiện dùng cho hạ tầng local; API/frontend vẫn có thể chạy trực tiếp khi phát triển.
- `apps/rag_api` cũ đã được loại bỏ; dùng `apps/chat_api` cho chatbot product API.
- Không commit `.env`, data generated, logs hoặc artifacts lớn.
