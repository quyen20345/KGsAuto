# KGsAuto

Hệ thống tự động xây dựng Knowledge Graph từ tài liệu tiếng Việt, sử dụng LLM để trích xuất thực thể và quan hệ, xử lý trùng lặp, import vào Neo4j, index vào Qdrant, và cung cấp API/frontend để truy vấn.

## Kiến trúc

```
Markdown → Extraction (LLM) → Entity Resolution → Neo4j + Qdrant → Graph/Chat/Pipeline API → Frontend
```

Xem hướng dẫn cài đặt chi tiết: **[SETUP.md](SETUP.md)**

## Chạy nhanh bằng Docker

```bash
docker compose up -d
```

Tất cả services được khởi động: Neo4j, Qdrant, Graph API, Pipeline API, Chat API, Frontend.

| URL | Mô tả |
|-----|-------|
| http://localhost:3000 | Frontend UI |
| http://localhost:7474 | Neo4j Browser (neo4j/12345678) |
| http://localhost:6333/dashboard | Qdrant Dashboard |

## Chạy dev mode (không Docker)

```bash
# Yêu cầu: Python 3.12+, Node.js, Docker (chạy Neo4j + Qdrant)
cp .env.example .env   # Điền API key LLM
docker compose up -d neo4j qdrant   # Chỉ chạy hạ tầng
pip install -r requirements.txt && pip install -e . --no-deps
cd apps/frontend && npm install && cd ../..
./run.sh dev
```

## Giao diện

### Xem chi tiết thực thể

![Entity View](project/docs/assets/ui-entity.png)

### So sánh và merge thực thể trùng lặp

![Compare Entities](project/docs/assets/ui-compare.png)

## Pipeline chính

1. **Upload / Crawl** — Markdown đầu vào từ `data/raw/` hoặc crawl web
2. **Extraction** — LLM trích xuất entities và relationships ra KG JSON
3. **Entity Resolution** — Chuẩn hóa, blocking, clustering, matching thực thể trùng
4. **Import Neo4j** — Import KG đã resolve vào Neo4j + index Qdrant

Tất cả các bước chạy qua Pipeline API (`localhost:8001/docs`) hoặc qua UI Pipeline Dashboard.

## API

| Service | Port | Docs | Mô tả |
|---------|------|------|-------|
| Graph API | 8000 | /docs | Truy vấn graph, tìm kiếm entity, merge |
| Pipeline API | 8001 | /docs | Upload, crawl, extract, resolve, import |
| Chat API | 8002 | /docs | Chat RAG (semantic, graph, hybrid) |

## Cấu trúc thư mục

```
├── apps/              # Frontend (React/Vite) + 3 FastAPI apps
├── services/          # Pipeline, RAG, extraction, entity_resolution...
├── scripts/           # Script vận hành, backfill, visualize
├── docker/            # Dockerfile.backend (dùng chung 3 API)
├── data/              # Dữ liệu, exports, archives
├── project/           # Tài liệu, assets (ảnh UI)
├── docker-compose.yaml
├── run.sh             # Quick start script
├── SETUP.md           # Hướng dẫn cài đặt chi tiết
├── requirements.txt
└── pyproject.toml
```

## Export / Import dữ liệu Neo4j

```bash
# Export
docker exec kgsauto_neo4j cypher-shell -u neo4j -p 12345678 \
  "CALL apoc.export.cypher.all('/exports/neo4j_backup.cypher',
    {format:'cypher-shell', useOptimizations:{type:'UNWIND_BATCH', unwindBatchSize:1000}})
   YIELD file, nodes, relationships RETURN file, nodes, relationships"

# Import
docker exec -i kgsauto_neo4j cypher-shell -u neo4j -p 12345678 < data/exports/neo4j_backup.cypher
```

File backup hiện tại: `data/exports/neo4j_backup.cypher` (5.265 nodes, 9.653 relationships).

## Kiểm thử

```bash
python -m pytest apps/chat_api/tests apps/graph_api/tests apps/pipeline_api/tests -q
python -m pytest services/rag_system/tests services/entity_resolution/tests -q
cd apps/frontend && npm run lint && npm run build
```

## Archive

Các file archive lưu trong `data/archives/`:

| File | Nội dung |
|------|----------|
| `thesis.zip` | Mã nguồn LaTeX + PDF luận văn |
| `slide.zip` | PPTX + PDF báo cáo |
| `evaluation.zip` | Dữ liệu đánh giá RAG pipeline |
| `data.zip` | Archive dữ liệu cũ |
