# Hướng dẫn cài đặt và sử dụng KGsAuto

## Yêu cầu hệ thống

- **Docker** + Docker Compose (>= 2.0)
- **Conda** + Python 3.12 (nếu chạy dev mode)
- **Node.js 22+** (nếu chạy dev mode)
- Ổ cứng trống ~2GB cho dữ liệu

## 1. Tải project và dữ liệu

```bash
# Clone project
git clone https://github.com/quyen20345/KGsAuto.git
cd KGsAuto

# Tải và giải nén dữ liệu (từ Google Drive)
# Link: <link>
unzip KGsAuto_data.zip
# Cấu trúc sau giải nén:
#   data/docker/       - Neo4j + Qdrant volumes (647MB)
#   data/raw/          - Markdown nguồn
#   data/extracted/    - KG JSON đã extract
#   data/exports/      - Backup Neo4j (*.cypher)
#   data/mock_data/    - Dữ liệu mẫu cho test
#   data/pipeline_state.db - Trạng thái pipeline
```

## 2. Cài đặt nhanh (tự động)

```bash
./run.sh setup
```

Lệnh này sẽ: tạo conda env `py312`, cài Python packages, cài frontend dependencies, khởi động Neo4j + Qdrant.

## 3. Cấu hình môi trường

```bash
cp .env.example .env
```

Mở `.env` và điền các biến cần thiết:

```bash
# LLM Provider (bắt buộc)
OPENAI_COMPATIBLE_API_KEY=your-api-key
OPENAI_COMPATIBLE_BASE_URL=https://api.deepseek.com   # hoặc OpenAI, v.v.
OPENAI_COMPATIBLE_MODEL=deepseek-v4-flash

# Neo4j (mặc định đã đúng cho Docker)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=12345678

# Qdrant
QDRANT_URL=http://localhost:6333
```

## 4. Chạy toàn bộ hệ thống bằng Docker

```bash
# Khởi động tất cả services
docker compose up -d

# Kiểm tra trạng thái
docker compose ps

# Xem logs
docker compose logs -f
```

**Các services:**
| Service | Port | Mô tả |
|---------|------|-------|
| Frontend | 3000 | Giao diện web |
| Graph API | 8000 | Truy vấn graph, tìm kiếm entity |
| Pipeline API | 8001 | Upload, crawl, extract, resolve, import |
| Chat API | 8002 | Chat RAG (semantic, graph, hybrid) |
| Neo4j | 7474 | Browser + 7687 Bolt |
| Qdrant | 6333 | Vector database |

**URL chính:**
- Frontend: http://localhost:3000
- Neo4j Browser: http://localhost:7474 (neo4j / 12345678)
- Graph API Docs: http://localhost:8000/docs
- Pipeline API Docs: http://localhost:8001/docs

## 5. Dừng hệ thống

```bash
docker compose down          # Dừng, giữ dữ liệu
docker compose down -v       # Dừng và XÓA toàn bộ dữ liệu volumes
```

## 6. Import/Export dữ liệu Neo4j

### Export ra file

```bash
docker exec kgsauto_neo4j cypher-shell -u neo4j -p 12345678 \
  "CALL apoc.export.cypher.all('/exports/neo4j_backup.cypher',
    {format:'cypher-shell', useOptimizations:{type:'UNWIND_BATCH', unwindBatchSize:1000}})
   YIELD file, nodes, relationships RETURN file, nodes, relationships"
# File lưu tại: data/exports/neo4j_backup.cypher
```

### Import từ file

```bash
cat data/exports/neo4j_backup.cypher | \
  docker exec -i kgsauto_neo4j cypher-shell -u neo4j -p 12345678
```

## 7. Chạy Pipeline (tạo Knowledge Graph mới)

Pipeline gồm 4 bước qua Pipeline API (port 8001) hoặc qua UI Pipeline Dashboard:

### Bước 1: Crawl / Upload Markdown
```bash
# Crawl từ URL
curl -X POST http://localhost:8001/api/crawl \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://example.com/page"]}'

# Hoặc upload file Markdown qua UI Pipeline Dashboard
```

### Bước 2: Extract KG
```bash
python -m services.extraction.cli \
  --input-dir data/raw/uet \
  --output-dir data/extracted \
  --provider OpenAICompatible \
  --model deepseek-v4-flash
```

### Bước 3: Entity Resolution
```bash
python -m services.entity_resolution.cli \
  --stage all \
  --input-dir data/extracted \
  --store-backend memory \
  --run-id my_run
```

### Bước 4: Import vào Neo4j
```bash
python -m services.neo4j_import.import_to_neo4j \
  --dir data/entity_resolution/artifacts/final/stage3/output_graph
```

## 8. Chạy Dev Mode (không Docker cho backend)

```bash
# Cài đặt toàn bộ (chạy 1 lần)
./run.sh setup

# Hoặc cài thủ công:
conda activate py312                          # Kích hoạt conda env
docker compose up -d neo4j qdrant             # Chạy hạ tầng
pip install -r requirements.txt               # Python packages
pip install -e . --no-deps
cd apps/frontend && npm install && cd ../..   # Frontend

# Chạy tất cả
conda activate py312
./run.sh dev

# Hoặc chạy riêng lẻ
./run.sh api       # Chỉ 3 API
./run.sh frontend  # Chỉ frontend
```

## 9. Kiểm thử

```bash
# Backend tests
python -m pytest apps/chat_api/tests apps/graph_api/tests apps/pipeline_api/tests -q
python -m pytest services/rag_system/tests services/entity_resolution/tests -q

# Frontend
cd apps/frontend && npm run lint && npm run build
```

## 10. Cấu trúc thư mục

```
KGsAuto/
├── apps/                  # Frontend (React) + 3 FastAPI apps
│   ├── frontend/          #   Dockerfile + nginx.conf
│   ├── graph_api/         #   API truy vấn graph
│   ├── pipeline_api/      #   API pipeline
│   └── chat_api/          #   API chatbot RAG
├── services/              # Pipeline, RAG, extraction, ER...
├── scripts/               # Script vận hành
├── docker/                # Dockerfile.backend
├── data/                  # Dữ liệu (gitignored)
│   ├── docker/            #   Neo4j + Qdrant volumes
│   ├── raw/               #   Markdown nguồn
│   ├── extracted/         #   KG JSON output
│   ├── exports/           #   Neo4j backup
│   └── archives/          #   Thesis, slide, evaluation zip
├── docker-compose.yaml    # Cấu hình Docker toàn bộ stack
├── run.sh                 # Quick start script
├── requirements.txt
└── pyproject.toml
```

## 11. Khắc phục sự cố thường gặp

**Neo4j không khởi động:**
```bash
docker compose down neo4j && docker compose up -d neo4j
```

**Không kết nối được LLM:**
Kiểm tra `.env` đã có `OPENAI_COMPATIBLE_API_KEY` và `OPENAI_COMPATIBLE_BASE_URL` đúng.

**Frontend không load được API (Docker):**
Kiểm tra nginx proxy trong frontend container:
```bash
docker exec kgsauto_frontend nginx -t
```

**Port bị chiếm:**
```bash
# Kiểm tra port đang dùng
sudo lsof -i :3000 :8000 :8001 :8002 :7474 :7687 :6333
```

**Reset toàn bộ dữ liệu:**
```bash
docker compose down -v
rm -rf data/docker/
docker compose up -d
# Sau đó import lại từ backup
cat data/exports/neo4j_backup.cypher | docker exec -i kgsauto_neo4j cypher-shell -u neo4j -p 12345678
```
