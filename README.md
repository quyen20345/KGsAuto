# KGsAuto - Knowledge Graph Automation System

## Quick Start

### 1. Khởi động Docker services:

```bash
cd /home/quyen/Documents/KGsAuto
docker compose up -d
```

### 2. Khởi động Backend (terminal 1):

```bash
uvicorn apps.backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Khởi động Frontend (terminal 2):

```bash
cd apps/frontend && npm run dev
```

## Truy cập

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000/docs
- Neo4j Browser: http://localhost:7474 (user: neo4j, pass: 12345678)
- Qdrant Dashboard: http://localhost:6333/dashboard

## Tài liệu đầy đủ

Xem file [CLAUDE.md](CLAUDE.md) để biết thêm chi tiết về:
- Kiến trúc hệ thống
- Cài đặt môi trường
- Chạy pipeline trích xuất
- Entity resolution pipeline
- Các lệnh hữu ích
- Xử lý sự cố
- API endpoints