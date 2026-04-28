# KGsAuto - Knowledge Graph Automation System

## Chạy nhanh các services

### Cách đơn giản nhất

Mở 3 terminal tại thư mục project `/Browser/quyen/Documents/KGsAuto` và chạy:

#### Terminal 1 - Hạ tầng Docker
```bash
docker compose up -d
```

Lệnh này sẽ khởi động các services nền:
- Neo4j
- Qdrant
- Ollama

#### Terminal 2 - Backend API
```bash
uvicorn apps.backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Terminal 3 - Frontend
```bash
cd apps/frontend && npm run dev
```

## Các địa chỉ sau khi chạy

- Frontend: http://localhost:5173
- Backend API Docs: http://localhost:8000/docs
- Neo4j Browserr: http://localhost:7474
  - user: `neo4j`
  - password: `12345678`
- Qdrant Dashboard: http://localhost:6333/dashboard
- Ollama API: http://localhost:11434

## Dừng services

### Dừng frontend/backend
Nhấn `Ctrl + C` ở terminal đang chạy.

### Dừng Docker services
```bash
docker compose down
```

## Chạy extract knowledge graph

Chạy từ thư mục gốc của repo:

```bash
python -m services.extraction.cli \
  --input-dir data/raw/uet \
  --output-dir data/extracted \
  --provider OpenAICompatible \
  --model cx/gpt-5.3-codex
```

Kết quả sẽ được ghi vào thư mục `data/extracted`.

### Một số lệnh hay dùng

Chạy lại toàn bộ, bỏ qua chế độ skip file đã tồn tại:

```bash
python -m services.extraction.cli \
  --input-dir data/raw/uet \
  --output-dir data/extracted \
  --provider OpenAICompatible \
  --model cx/gpt-5.3-codex \
  --no-skip-existing
```

Xem toàn bộ options:

```bash
python -m services.extraction.cli --help
```

## Chạy entity resolution

### Cách đơn giản nhất

Nếu chỉ muốn chạy nhanh toàn bộ pipeline 3 stage:

```bash
python -m services.entity_resolution.cli \
  --stage all \
  --input-dir data/extracted \
  --store-backend memory \
  --run-id demo_run
```

Lưu ý:
- `memory` nhanh nhưng không lưu dữ liệu giữa các lần chạy.
- Với `memory`, nên dùng `--stage all` trong một lệnh.

### Chạy từng stage với backend lưu trữ bền vững

Nếu muốn chạy riêng từng stage, dùng `qdrant`:

#### Stage 1
```bash
python -m services.entity_resolution.cli \
  --stage stage1 \
  --input-dir data/extracted \
  --store-backend qdrant \
  --run-id my_run
```

#### Stage 2
```bash
python -m services.entity_resolution.cli \
  --stage stage2 \
  --store-backend qdrant \
  --run-id my_run
```

#### Stage 3
```bash
python -m services.entity_resolution.cli \
  --stage stage3 \
  --store-backend qdrant \
  --run-id my_run
```

### Một số option hay dùng

- `--llm-provider OpenAICompatible`
- `--llm-model cx/gpt-5.3-codex`
- `--enable-llm-blocking`
- `--no-llm-blocking`
- `--cluster-threshold 0.72`

## Neo4j
python apps/backend/neo4j/scripts/import_to_neo4j.py   --dir /home/quyen/Documents/KGsAuto/data/entity_resolution/artifacts/final/stage3/output_graph

python -m services.entity_resolution.cli   --stage all   --input-dir /home/quyen/Documents/KGsAuto/data/test_canonical_name_realdata/stage3/output_graph   --store-backend memory   --run-id final   --cluster-threshold 0.6   --enable-llm-blocking

python -m apps.backend.neo4j.scripts.add_embeddings_to_neo4j

 python -m apps.backend.neo4j.scripts.create_vector_index

## Ghi chú

- Luôn chạy các lệnh từ thư mục gốc của repo.
- Trước khi chạy extract hoặc entity resolution, hãy đảm bảo Docker services đã chạy (`docker compose up -d`).
- Nếu frontend chưa chạy được, vào `apps/frontend` và cài dependencies bằng `npm install`.