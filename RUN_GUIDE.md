# Hướng dẫn chạy nhanh KGsAuto

File này tóm tắt các lệnh thường dùng để chạy backend, frontend và pipeline đánh giá RAG.

## 1. Chuẩn bị môi trường

```bash
pip install -r requirements.txt
pip install -e . --no-deps
```

Nếu dùng Conda:

```bash
conda activate py312
```

Khởi động hạ tầng cần thiết:

```bash
docker compose up -d
```

Các service chính trong Docker Compose gồm Neo4j, Qdrant và Ollama.

## 2. Chạy backend

### Graph API

Graph API phục vụ truy vấn graph, tìm kiếm thực thể, xem chi tiết entity và thao tác merge.

```bash
uvicorn apps.graph_api.main:app --host 0.0.0.0 --port 8000 --reload
```

URL mặc định:

```text
http://localhost:8000
```

### Chat API

Chat API phục vụ hỏi đáp RAG với các chế độ Semantic Search, Naive Graph RAG, Graph Search và Hybrid RAG.

```bash
uvicorn apps.chat_api.main:app --host 0.0.0.0 --port 8002 --reload
```

URL mặc định:

```text
http://localhost:8002
```

Một số endpoint hữu ích:

```text
GET  /health
GET  /modes
POST /query
GET  /v1/models
POST /v1/chat/completions
```

## 3. Chạy frontend

```bash
cd apps/frontend
npm install
npm run dev
```

Frontend mặc định chạy ở:

```text
http://localhost:5173
```

Các biến môi trường frontend thường dùng:

```text
VITE_GRAPH_API_BASE_URL=http://localhost:8000
VITE_API_BASE_URL=http://localhost:8000
VITE_CHAT_API_BASE_URL=http://localhost:8002
```

## 4. Chuẩn bị Qdrant: Re-embed dữ liệu

Khi cần re-embed toàn bộ dữ liệu markdown lên Qdrant (ví dụ sau khi import Neo4j mới hoặc cập nhật dữ liệu):

```bash
# Xóa collection cũ
python -m services.rag_system.cli delete-collection

# Tạo collection mới
python -m services.rag_system.cli create-collection

# Index toàn bộ (không limit)
python -m services.rag_system.cli index --force
```

Hoặc kiểm tra kết nối trước:

```bash
python -m services.rag_system.cli test-connections
```

Lưu ý:
- Neo4j phải chạy và có dữ liệu đã import
- `.env` phải có `OPENAI_COMPATIBLE_*` hoặc `GOOGLE_API_KEY` cho embedding

## 5. Chạy evaluation runner

Runner dùng để chạy một hoặc nhiều chế độ RAG trên tập câu hỏi và lưu kết quả raw.

### Chạy so sánh tất cả mode

```bash
conda run -n py312 python -m services.rag_system.cli evaluate run-comparison \
  --dataset data/evaluation/testset_clean_30.csv \
  --output data/evaluation/rag_eval_comparison.jsonl \
  --verbose
```

### Chạy một mode cụ thể

Ví dụ chạy Hybrid RAG:

```bash
conda run -n py312 python -m services.rag_system.cli evaluate run \
  --dataset data/evaluation/testset_clean_30.csv \
  --mode hybrid \
  --output data/evaluation/hybrid_results.jsonl
```

Các mode hợp lệ:

```text
semantic_search
graph_search
naive_grag
hybrid
```

Output chính:

```text
*.jsonl   kết quả đầy đủ từng câu hỏi
*.csv     bản CSV tương ứng
```

## 6. Chạy RAGAS scoring

Scoring dùng RAGAS để chấm các kết quả đã sinh từ runner.

### Chấm với metric mặc định

```bash
conda run -n py312 python -m services.rag_system.cli evaluate score \
  --results data/evaluation/rag_eval_comparison.jsonl \
  --output data/evaluation/rag_eval_scored.jsonl
```

### Chọn metric cụ thể

```bash
conda run -n py312 python -m services.rag_system.cli evaluate score \
  --results data/evaluation/hybrid_results.jsonl \
  --output data/evaluation/hybrid_scored.jsonl \
  --metric faithfulness \
  --metric context_precision \
  --metric context_recall
```

Output chính:

```text
*_scored.jsonl       kết quả đã chấm từng mẫu
*_scored.csv         bản CSV tương ứng
*_scored.summary.csv thống kê trung bình theo mode
```

## 7. Gợi ý thứ tự chạy đầy đủ

```bash
# 1. Hạ tầng
docker compose up -d

# 2. Backend
uvicorn apps.graph_api.main:app --host 0.0.0.0 --port 8000 --reload
uvicorn apps.chat_api.main:app --host 0.0.0.0 --port 8002 --reload

# 3. Frontend
cd apps/frontend && npm install && npm run dev

# 4. Re-embed dữ liệu lên Qdrant
python -m services.rag_system.cli delete-collection
python -m services.rag_system.cli create-collection
python -m services.rag_system.cli index --force

# 5. Evaluation runner
conda run -n py312 python -m services.rag_system.cli evaluate run-comparison \
  --dataset data/evaluation/testset_clean_30.csv \
  --output data/evaluation/rag_eval_comparison.jsonl

# 6. RAGAS scoring
conda run -n py312 python -m services.rag_system.cli evaluate score \
  --results data/evaluation/rag_eval_comparison.jsonl \
  --output data/evaluation/rag_eval_scored.jsonl
```

Lưu ý: Graph Search và Hybrid RAG có thể tốn nhiều thời gian và nhiều lượt gọi LLM hơn Semantic Search.
