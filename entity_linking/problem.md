### 1. Nút thắt lớn nhất: Gọi LLM tuần tự (LLM API Bottleneck)

* **Vấn đề:** Trong hàm `entity_link_iteration`, bạn vòng lặp qua 100.000 IDs. Với mỗi ID có ứng viên (candidates), bạn gọi hàm `_ask_llm`.
* **Hậu quả:** Giả sử 50% số entities có ứng viên, bạn sẽ phải gọi LLM khoảng 50.000 lần cho mỗi iteration (vòng lặp).
* *Thời gian:* Nếu 1 request LLM mất 2 giây, 50.000 requests tuần tự sẽ mất khoảng **27 tiếng** cho MỘT vòng lặp.
* *Chi phí:* Số lượng token xử lý sẽ khổng lồ, dẫn đến tốn rất nhiều tiền (nếu dùng API trả phí) hoặc bị chặn do vượt quá Rate Limit (giới hạn request/phút).



### 2. Lỗi so sánh thừa (Redundant Comparisons)

* **Vấn đề:** Biến `processed` của bạn hiện tại chỉ lưu lại những `merge_ids` **đã được gộp thành công**. Nó không lưu những cặp đã so sánh nhưng **bị LLM từ chối gộp**.
* **Hậu quả:** * Lượt 1: Thực thể A tìm thấy B. LLM bảo "KHÔNG MERGE".
* Lượt 2: Vòng lặp chạy đến thực thể B. B tìm thấy A. Bạn lại gọi LLM lần nữa để hỏi cặp (B, A) và LLM lại bảo "KHÔNG MERGE".
* Điều này làm lãng phí gấp đôi số lần gọi LLM vô ích.



### 3. Vấn đề "N+1 Query" với Qdrant

* **Vấn đề:** Bạn gọi `store.get_all_entity_ids()` để lấy 100.000 IDs. Sau đó trong vòng lặp `for`, bạn lại gọi `store.get_entity_by_id(entity_id)` 100.000 lần.
* **Hậu quả:** Tạo ra 100.000 network requests đồng bộ tới Qdrant chỉ để lấy dữ liệu gốc, gây chậm hệ thống không cần thiết.

### 4. Ngưỡng tương đồng (Score Threshold) quá thấp

* **Vấn đề:** Tham số `score_threshold = 0.5` mặc định là quá thấp đối với Cosine Similarity.
* **Hậu quả:** Nó sẽ trả về rất nhiều "ứng viên rác" (không liên quan nhưng có chút từ vựng giống nhau). LLM sẽ phải đọc và xử lý một lượng text khổng lồ cho những ứng viên không đáng để so sánh.

---

### Cách tối ưu hóa (Optimization Strategy) cho 100.000 Entities

Để code chạy được với data lớn, bạn cần cấu trúc lại theo các bước sau:

**1. Tăng `score_threshold` lên mức an toàn**
Chỉ nên đưa cho LLM những ứng viên có độ tương đồng vector thực sự cao. Hãy nâng `score_threshold` lên khoảng **`0.8` hoặc `0.85**` (tùy vào model embedding của bạn).

**2. Lưu lịch sử các cặp đã so sánh (Cache Attempted Pairs)**
Thêm một set `attempted_pairs` để nhớ các cặp đã hỏi LLM để không hỏi lại.

```python
attempted_pairs = set()

# Trước khi gọi LLM:
pair_key = frozenset([seed_id, candidate_id])
if pair_key in attempted_pairs:
    continue # Bỏ qua ứng viên này
attempted_pairs.add(pair_key)

```

**3. Tối ưu truy vấn Qdrant (Dùng Scroll with Payload)**
Thay vì lấy ID rồi query lại, hãy lấy trực tiếp data bằng `scroll`. Trong `entity_store.py`, bạn có thể viết một hàm `yield_all_entities()` dùng `scroll` để trả về từng batch thực thể có sẵn payload.

**4. Xử lý đa luồng (Multithreading/Async) - Bắt buộc**
Bạn không thể gọi LLM tuần tự. Cần sử dụng `concurrent.futures.ThreadPoolExecutor` hoặc `asyncio` để gửi các request lên LLM song song (ví dụ: batch 20-50 requests cùng lúc, có xử lý catch Rate Limit).

**5. Gom cụm trước khi dùng LLM (Clustering - Nâng cao)**
Thay vì $O(N)$ vòng lặp duyệt từng entity, một kỹ thuật tiêu chuẩn cho 100k vectors là:

* Dùng thuật toán Gom cụm (như DBSCAN hoặc HNSW clustering) dựa trên vector embeddings để tạo ra các "cụm" (clusters) thực thể giống nhau.
* Chỉ sử dụng LLM để đối chiếu và hợp nhất các thực thể **nằm trong cùng một cụm nhỏ**.

---

**Bạn có muốn tôi viết lại hàm `entity_link_iteration` áp dụng cơ chế *Caching cặp đã so sánh* và xử lý đa luồng (Thread Pool) để giải quyết nút thắt tốc độ không?**