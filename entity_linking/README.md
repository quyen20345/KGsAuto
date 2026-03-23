# Entity Linking Module - Tài liệu Chi tiết

## Tổng Quan

Module `entity_linking` là hệ thống **giải quyết trùng lặp thực thể (Entity Resolution)** cho Đồ thị Kiến thức Việt Nam. Nó sử dụng kết hợp **tìm kiếm vector tương tự** và **quyết định dựa trên LLM** để xác định và hợp nhất các thực thể trùng lặp trên các tệp đồ thị kiến thức.

**Mục đích chính:**
- Phát hiện các thực thể trùng lặp (cùng một đối tượng thực tế nhưng có ID khác nhau)
- Hợp nhất chúng thành một thực thể chính tắc duy nhất
- Cập nhật tất cả các liên kết trong đồ thị kiến thức
- Duy trì lịch sử hợp nhất để theo dõi nguồn gốc dữ liệu

---

## Cấu Trúc Thư Mục

```
entity_linking/
├── __init__.py                              # Marker gói Python
├── cli.py                                   # Giao diện dòng lệnh
├── entity_store.py                          # Wrapper vector store (Qdrant)
├── linker.py                                # Logic liên kết cốt lõi với LLM
├── pipeline.py                              # Điều phối quy trình làm việc toàn bộ
├── entity_linking_pipeline.md              # Tài liệu quy trình
├── entity_linking_technical_deep_dive.md   # Chi tiết kỹ thuật
└── logs/                                    # Nhật ký phát triển & vấn đề
    ├── bugs.md                              # Báo cáo lỗi
    ├── problem.md                           # Vấn đề hiệu suất
    ├── prompts.txt                          # Mẫu prompt
    ├── demo.py                              # Script demo/test
    ├── __main__.py                          # Điểm vào module
    └── mock_entity/                         # Dữ liệu giả để kiểm tra
```

---

## Các Thành Phần Cốt Lõi

### 1. EntityDB (entity_store.py)

**Mục đích:** Wrapper cho vector store để lưu trữ và tìm kiếm thực thể

**Công nghệ:**
- **Qdrant** - Cơ sở dữ liệu vector (chạy trên localhost:6333)
- **SentenceTransformer** - Mô hình nhúng (`all-MiniLM-L6-v2`)
- Kết hợp: `name + labels + aliases + description` thành văn bản có thể tìm kiếm

**Các phương thức chính:**

| Phương thức | Mục đích |
|------------|---------|
| `upsert_entities()` | Chèn/cập nhật thực thể với nhúng vector |
| `search_similar()` | Tìm thực thể tương tự bằng cosine similarity |
| `delete_entities()` | Xóa thực thể đã hợp nhất |
| `iter_entities()` | Duyệt hàng loạt thực thể (tránh N+1 queries) |
| `get_entity_by_id()` | Lấy một thực thể theo ID |
| `get_all_entity_ids()` | Lấy tất cả ID thực thể |

**Cấu trúc dữ liệu thực thể:**
```python
{
    "entity_id": "person_001",
    "labels": ["PERSON"],
    "properties": {
        "name": "Nguyễn Văn A",
        "aliases": ["Nguyễn A", "N.V.A"],
        "description": "Giáo sư tại Đại học X",
        "source": ["doc_001", "doc_002"]
    },
    "merged_ids": ["person_002", "person_005"],  # Lịch sử hợp nhất
    "_score": 0.92  # Điểm tương tự (chỉ cho ứng viên)
}
```

---

### 2. Linker (linker.py)

**Mục đích:** Logic giải quyết thực thể cốt lõi sử dụng LLM

#### 2.1 Chiến lược Prompt LLM

Hệ thống sử dụng prompt **có cấu trúc bằng tiếng Việt** (`ENTITY_LINK_PROMPT`) với các quy tắc quyết định:

**Hợp nhất khi:**
- Cùng tên/bí danh
- Mẫu ID khớp
- Cùng nhãn + các thuộc tính xác định giống nhau

**Không bao giờ hợp nhất:**
- Tên cá nhân khác nhau
- Quan hệ cha-con
- Nhãn khác nhau
- Các thực thể khác nhau về ngữ nghĩa

**Nguyên tắc:** Khi không chắc chắn, không hợp nhất (ưu tiên độ chính xác)

#### 2.2 Định dạng JSON Output (Dòng 62-77)

**Nếu có hợp nhất:**
```json
{
  "merge_ids": ["candidate_id_1", "candidate_id_2"],
  "new_entity": {
    "id": "seed_id",
    "labels": ["PERSON"],
    "properties": {
      "name": "Tên đầy đủ nhất",
      "aliases": ["Tên khác"],
      "description": "Mô tả tổng hợp",
      "source": ["doc_id_1", "doc_id_2"]
    }
  }
}
```

**Nếu không hợp nhất:**
```json
{
  "merge_ids": [],
  "new_entity": null
}
```

**Lưu ý quan trọng:**
- ID seed luôn được bảo toàn làm ID chính tắc
- `labels` là hợp của các nhãn từ schema
- `source` là mảng các ID tài liệu gốc
- `merged_ids` theo dõi lịch sử các ID bị hấp thụ

#### 2.3 Schema Thực thể

Hệ thống hỗ trợ 10 loại thực thể:

| Loại | Nhãn | Thuộc tính |
|------|------|-----------|
| Người | PERSON | name, aliases, description, source |
| Tổ chức | ORGANIZATION | name, aliases, description, source |
| Ấn phẩm | PUBLICATION | name, aliases, description, source |
| Dự án | RESEARCH_PROJECT | name, aliases, description, source |
| Chuyên ngành | MAJOR | name, aliases, description, source |
| Khóa học | COURSE | name, aliases, description, source |
| Đối tác | PARTNER | name, aliases, description, source |
| Sự kiện | EVENT | name, aliases, description, source |
| Giải thưởng | AWARD | name, aliases, description, source |
| Cơ sở vật chất | FACILITY | name, aliases, description, source |

#### 2.4 Các Phương thức Chính

**`_format_candidates(candidates)`** (Dòng 86-95)
- Định dạng các ứng viên thành văn bản dễ đọc cho LLM
- Bao gồm: điểm tương tự, ID, nhãn, thuộc tính

**`_ask_llm(llm, seed, candidates)`** (Dòng 98-118)
- Xây dựng prompt với thực thể seed và ứng viên
- Gọi LLM và phân tích phản hồi JSON
- Xử lý lỗi phân tích JSON một cách nhẹ nhàng
- Trả về quyết định có cấu trúc

**`_pair_key(a, b)`** (Dòng 187-188)
- Tạo tuple chuẩn hóa để theo dõi các cặp thực thể đã thử
- Ngăn chặn so sánh dư thừa (A→B và B→A)

**`entity_link_iteration(...)`** (Dòng 190-287)
- Logic lặp chính với gọi LLM đồng thời
- **Tham số:**
  - `limit`: tối đa ứng viên trên mỗi seed (mặc định: 10)
  - `score_threshold`: điểm tương tự tối thiểu (mặc định: 0.85)
  - `max_workers`: kích thước thread pool (mặc định: 8)
  - `batch_size`: thực thể trên mỗi batch scroll (mặc định: 256)
- Sử dụng `ThreadPoolExecutor` cho gọi LLM song song
- Triển khai khử trùng qua set `attempted_pairs`
- Xác thực hợp nhất trước khi áp dụng

**`run_entity_linking(...)`** (Dòng 290-302)
- Điều phối nhiều lần lặp cho đến khi hội tụ
- Ghi nhật ký tiến độ và trả về thống kê tóm tắt

#### 2.5 Thuật toán Liên kết Thực thể

**Mỗi lần lặp:**

1. **Tải tất cả thực thể** từ EntityDB bằng scroll/batch
2. **Với mỗi thực thể seed:**
   - Tìm kiếm ứng viên tương tự bằng vector similarity
   - Lọc ra các thực thể đã xử lý và cặp trùng lặp
   - Gửi các tác vụ quyết định LLM đến thread pool
3. **Xử lý phản hồi LLM** khi hoàn thành:
   - Xác thực quyết định hợp nhất
   - Đảm bảo thực thể vẫn tồn tại (xử lý race conditions)
   - Cập nhật thực thể chính tắc với dữ liệu hợp nhất
   - Xóa thực thể bị hấp thụ
   - Theo dõi ID hợp nhất cho lịch sử
4. **Trả về số lần hợp nhất** để phát hiện hội tụ

**Nhiều lần lặp:**
- Chạy tối đa `max_iterations` (mặc định: 5)
- Dừng sớm nếu không có hợp nhất (hội tụ)
- Trả về thống kê: tổng hợp nhất, lần lặp sử dụng, thực thể còn lại

---

### 3. Pipeline (pipeline.py)

**Mục đích:** Điều phối end-to-end

**Quy trình làm việc:**

```
Bước 1: Tải tệp KG
  ↓
Bước 2: Thu thập thực thể
  ↓
Bước 3: Upsert vào vector store
  ↓
Bước 4: Chạy entity linking
  ↓
Bước 5: Xây dựng bảng remap ID
  ↓
Bước 6: Viết lại tệp KG
```

**Chi tiết từng bước:**

**Bước 1: Tải tệp KG**
- Đọc tất cả tệp `*_kg.json` từ thư mục đầu vào
- Mỗi tệp chứa `nodes` và `relationships`

**Bước 2: Thu thập thực thể**
- Trích xuất tất cả các nút duy nhất trên các tệp
- Hợp nhất thuộc tính nếu cùng ID xuất hiện trong nhiều tệp

**Bước 3: Upsert vào vector store**
- Tạo/kết nối đến collection Qdrant
- Tạo nhúng và lưu trữ thực thể

**Bước 4: Chạy entity linking**
- Lặp lại tìm và hợp nhất thực thể trùng lặp
- Sử dụng LLM để đưa ra quyết định hợp nhất

**Bước 5: Xây dựng bảng remap ID**
- Tạo ánh xạ: `old_id → canonical_id`
- Dựa trên lịch sử `merged_ids`

**Bước 6: Viết lại tệp KG**
- Cập nhật ID nút thành ID chính tắc
- Remap `start_id`/`end_id` của quan hệ
- Xóa self-loops được tạo bởi hợp nhất
- Khử trùng quan hệ bằng `(start, type, end)`
- Viết tệp đã làm sạch vào thư mục đầu ra

---

### 4. CLI (cli.py)

**Mục đích:** Giao diện dòng lệnh

**Cấu hình (Biến môi trường):**

| Biến | Mô tả | Mặc định |
|------|-------|---------|
| `EL_KG_DIR` | Thư mục đầu vào | `data/extracted` |
| `EL_OUTPUT_DIR` | Thư mục đầu ra | `data/import_linked` |
| `EL_MODEL` | Mô hình LLM | `gpt-5` |
| `EL_PROVIDER` | Nhà cung cấp LLM | `proxypal` |
| `EL_MAX_ITERATIONS` | Tối đa lần lặp | `10` |
| `EL_SCORE_THRESHOLD` | Ngưỡng tương tự | `0.85` |
| `EL_LIMIT` | Tối đa ứng viên/thực thể | `10` |
| `EL_MAX_WORKERS` | Thread LLM đồng thời | `8` |
| `EL_LOG_LEVEL` | Mức ghi nhật ký | `INFO` |

**Cách sử dụng:**
```bash
python -m entity_linking.cli
```

---

## Luồng Dữ Liệu: Đầu vào → Đầu ra

```
1. Đầu vào: data/extracted/*_kg.json
   ↓
2. Trích xuất tất cả nút → thực thể duy nhất
   ↓
3. Tạo nhúng → lưu trữ trong Qdrant
   ↓
4. Với mỗi thực thể:
   - Tìm kiếm vector → tìm ứng viên tương tự
   - Quyết định LLM → hợp nhất hoặc không
   - Cập nhật thực thể chính tắc + xóa các thực thể hợp nhất
   ↓
5. Xây dựng bảng remap (old → canonical)
   ↓
6. Viết lại tệp KG:
   - Thay thế nút hợp nhất bằng nút chính tắc
   - Remap tất cả ID quan hệ
   - Xóa trùng lặp & self-loops
   ↓
7. Đầu ra: data/import_linked/*_kg.json
```

---

## Cách Sử Dụng

### Sử dụng CLI

```bash
# Cấu hình biến môi trường (tùy chọn)
export EL_KG_DIR="data/extracted"
export EL_OUTPUT_DIR="data/import_linked"
export EL_MAX_ITERATIONS=5
export EL_SCORE_THRESHOLD=0.85
export EL_MAX_WORKERS=8

# Chạy
python -m entity_linking.cli
```

### Sử dụng Lập trình

```python
from entity_linking.pipeline import run_pipeline

# Chạy quy trình đầy đủ
stats = run_pipeline(
    kg_dir="data/extracted",
    output_dir="data/import_linked",
    max_iterations=5,
    score_threshold=0.85,
    limit=10,
    max_workers=8
)

print(f"Tổng hợp nhất: {stats['total_merges']}")
print(f"Lần lặp: {stats['iterations']}")
print(f"Thực thể còn lại: {stats['remaining_entities']}")
```

---

## Tối ưu Hóa Hiệu Suất

Hệ thống sử dụng các kỹ thuật để xử lý hiệu quả các tập dữ liệu lớn:

| Kỹ thuật | Mục đích | Lợi ích |
|---------|---------|--------|
| **Tìm kiếm vector** | Giảm so sánh O(N²) thành O(N×K) | Tìm ứng viên nhanh hơn |
| **Khử trùng cặp** | Tránh gọi LLM cho cùng cặp hai lần | Giảm chi phí API |
| **Scroll hàng loạt** | Tránh vấn đề N+1 query | Truy vấn cơ sở dữ liệu hiệu quả |
| **Gọi LLM đồng thời** | ThreadPoolExecutor cho yêu cầu song song | Giảm thời gian chờ API |
| **Theo dõi lịch sử hợp nhất** | `merged_ids` duy trì dấu vết kiểm toán | Truy vết nguồn gốc dữ liệu |
| **Xác thực schema** | LLM bị ràng buộc vào loại thực thể hợp lệ | Đảm bảo tính nhất quán dữ liệu |
| **Khử trùng quan hệ** | Làm sạch các cạnh dư thừa sau hợp nhất | Đồ thị sạch hơn |

---

## Phụ Thuộc

**Dịch vụ:**
- **Qdrant** - Cơ sở dữ liệu vector (phải chạy trên localhost:6333)
- **LLM Provider** - ProxyPal hoặc API tương thích OpenAI

**Gói Python:**
- `qdrant-client` - Client Qdrant
- `sentence-transformers` - Mô hình nhúng
- `llms` - Module LLM tùy chỉnh

---

## Vấn Đề Đã Biết & Khắc Phục Sự Cố

### Vấn đề: Hệ thống bị treo

**Nguyên nhân:**
- Sử dụng mã tuần tự cũ (được comment trong linker.py)
- Gọi API LLM bị chặn
- Không có đồng thời = cực kỳ chậm trên tập dữ liệu lớn

**Giải pháp:**
- Đã tối ưu hóa với gọi LLM đồng thời qua ThreadPoolExecutor
- Khử trùng cặp để tránh so sánh dư thừa
- Ngưỡng điểm cao hơn (0.85) để giảm ứng viên sai
- Tải thực thể hàng loạt

### Vấn đề: Hợp nhất sai

**Nguyên nhân:**
- Ngưỡng tương tự quá thấp
- Prompt LLM không rõ ràng

**Giải pháp:**
- Tăng `EL_SCORE_THRESHOLD` (mặc định 0.85 là tốt)
- Xem xét prompt trong `linker.py` dòng 15-83
- Kiểm tra schema thực thể

### Vấn đề: Hiệu suất chậm

**Nguyên nhân:**
- Quá nhiều ứng viên trên mỗi thực thể
- Quá ít worker LLM
- Qdrant chậm

**Giải pháp:**
- Giảm `EL_LIMIT` (tối đa ứng viên)
- Tăng `EL_MAX_WORKERS` (nếu API cho phép)
- Kiểm tra kết nối Qdrant

---

## Ví dụ Dữ Liệu

### Đầu vào: Tệp KG

```json
{
  "nodes": [
    {
      "id": "person_001",
      "labels": ["PERSON"],
      "properties": {
        "name": "Nguyễn Văn A",
        "description": "Giáo sư"
      }
    },
    {
      "id": "person_002",
      "labels": ["PERSON"],
      "properties": {
        "name": "Nguyễn A",
        "description": "Giáo sư tại Đại học X"
      }
    }
  ],
  "relationships": [
    {
      "start_id": "person_001",
      "type": "WORKS_AT",
      "end_id": "org_001"
    }
  ]
}
```

### Quyết định LLM

```json
{
  "merge_ids": ["person_002"],
  "new_entity": {
    "id": "person_001",
    "labels": ["PERSON"],
    "properties": {
      "name": "Nguyễn Văn A",
      "aliases": ["Nguyễn A"],
      "description": "Giáo sư tại Đại học X",
      "source": ["doc_001", "doc_002"]
    }
  }
}
```

### Đầu ra: Tệp KG Đã Liên Kết

```json
{
  "nodes": [
    {
      "id": "person_001",
      "labels": ["PERSON"],
      "properties": {
        "name": "Nguyễn Văn A",
        "aliases": ["Nguyễn A"],
        "description": "Giáo sư tại Đại học X",
        "source": ["doc_001", "doc_002"]
      }
    }
  ],
  "relationships": [
    {
      "start_id": "person_001",
      "type": "WORKS_AT",
      "end_id": "org_001"
    }
  ]
}
```

---

## Kiến Trúc Tổng Quan

```
┌─────────────────────────────────────────────────────────┐
│                    CLI Entry Point                       │
│                   (cli.py)                               │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  Pipeline Orchestrator                   │
│                  (pipeline.py)                           │
│  - Tải tệp KG                                           │
│  - Thu thập thực thể                                    │
│  - Upsert vào vector store                              │
│  - Chạy entity linking                                  │
│  - Xây dựng bảng remap                                  │
│  - Viết lại tệp KG                                      │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
┌──────────────────┐    ┌──────────────────┐
│  Entity Linker   │    │   Entity Store   │
│  (linker.py)     │    │ (entity_store.py)│
│                  │    │                  │
│ - Tìm ứng viên   │    │ - Vector search  │
│ - Gọi LLM        │    │ - Upsert/Delete  │
│ - Hợp nhất       │    │ - Batch scroll   │
└────────┬─────────┘    └────────┬─────────┘
         │                       │
         └───────────┬───────────┘
                     ▼
            ┌──────────────────┐
            │  Qdrant Vector   │
            │   Database       │
            │ (localhost:6333) │
            └──────────────────┘
```

---

## Tài Liệu Bổ Sung

- `entity_linking_pipeline.md` - Chi tiết quy trình
- `entity_linking_technical_deep_dive.md` - Phân tích kỹ thuật sâu
- `logs/prompts.txt` - Mẫu prompt LLM
- `logs/demo.py` - Script demo

---

## Tóm Tắt

Module `entity_linking` là một hệ thống sản xuất được thiết kế tốt để giải quyết trùng lặp thực thể trong đồ thị kiến thức. Nó kết hợp tìm kiếm vector hiệu quả với quyết định dựa trên LLM để đạt được độ chính xác cao trong khi duy trì hiệu suất tốt thông qua các kỹ thuật tối ưu hóa như khử trùng cặp, gọi đồng thời và scroll hàng loạt.
