# Cách đánh giá trong khóa luận KGsAuto

Tài liệu này mô tả ngắn gọn cách đánh giá được sử dụng trong khóa luận. Trọng tâm đánh giá là **ứng dụng Knowledge Graph trong hệ thống hỏi đáp**, còn các giai đoạn xây dựng graph như trích xuất và Entity Resolution được báo cáo dưới dạng thống kê vận hành.

## 1. Mục tiêu đánh giá

Khóa luận hướng tới việc kiểm chứng vai trò của Knowledge Graph trong hệ thống hỏi đáp trên dữ liệu tiếng Việt về Trường Đại học Công nghệ. Câu hỏi đánh giá chính là:

> Knowledge Graph có giúp cải thiện quá trình hỏi đáp khi được kết hợp với bằng chứng văn bản trong RAG hay không?

Vì vậy, phần đánh giá tập trung vào việc so sánh các chế độ truy xuất khác nhau trong hệ thống RAG:

- `semantic_search`: truy xuất văn bản bằng vector search.
- `naive_grag`: truy xuất graph context trực tiếp từ Knowledge Graph.
- `graph_search`: truy xuất và reasoning trên graph theo nhiều bước.
- `hybrid`: kết hợp bằng chứng văn bản và bằng chứng graph.

## 2. Vì sao extraction và Entity Resolution chỉ báo cáo thống kê

Hai giai đoạn trích xuất Knowledge Graph và Entity Resolution là các bước nền tảng để tạo graph đầu vào cho hệ thống hỏi đáp. Tuy nhiên, trong phạm vi khóa luận hiện tại, chưa có tập ground truth đủ tin cậy để đánh giá định lượng độ chính xác của hai giai đoạn này.

Cụ thể:

- Với extraction, cần ground truth về thực thể, quan hệ và thuộc tính đúng trong từng tài liệu.
- Với Entity Resolution, cần nhãn cho các cặp hoặc cụm thực thể đồng tham chiếu.
- Việc xây dựng các tập nhãn này tốn nhiều công sức và cần tiêu chuẩn annotation rõ ràng.

Do đó, khóa luận không báo cáo precision, recall hoặc F1 cho extraction và Entity Resolution. Thay vào đó, các giai đoạn này được mô tả bằng thống kê vận hành, ví dụ:

- số tài liệu Markdown đầu vào,
- số tài liệu xử lý thành công,
- số node và relationship được trích xuất,
- số thực thể trước và sau Entity Resolution,
- số cụm ứng viên,
- số canonical entity,
- số relationship trước và sau rewiring.

Các số liệu này giúp mô tả quy mô xử lý và artifact sinh ra, nhưng không được diễn giải như độ chính xác của pipeline.

## 3. Đánh giá hệ thống hỏi đáp bằng RAGAS

Phần đánh giá chính của khóa luận sử dụng RAGAS để đánh giá chất lượng hỏi đáp. RAGAS phù hợp với mục tiêu này vì nó đánh giá hệ thống RAG dựa trên câu hỏi, câu trả lời, context được truy xuất và reference answer.

Các metric chính dự kiến sử dụng gồm hai nhóm: metric RAGAS và metric vận hành.

### Metric RAGAS

| Metric | Ý nghĩa | Ghi chú |
|---|---|---|
| `faithfulness` | Mức độ các khẳng định trong câu trả lời được hỗ trợ bởi context truy xuất. | Không yêu cầu reference answer. |
| `answer_correctness` | Mức độ câu trả lời đúng so với reference answer. | Cần reference answer; thường tốn thêm chi phí evaluator. |
| `answer_relevancy` | Mức độ câu trả lời liên quan trực tiếp đến câu hỏi. | Có thể cần embedding/evaluator tùy cấu hình RAGAS. |
| `context_precision` | Mức độ các context truy xuất có liên quan đến câu hỏi/reference. | Cần reference answer hoặc reference contexts. |
| `context_recall` | Mức độ context truy xuất bao phủ thông tin cần thiết trong reference answer. | Cần reference answer. |

Trong khóa luận, các metric tối thiểu nên báo cáo là `faithfulness`, `context_precision` và `context_recall`. Nếu chi phí chấm điểm cho phép, có thể bổ sung `answer_correctness` và `answer_relevancy` để đánh giá trực tiếp hơn chất lượng câu trả lời.

### Metric vận hành

| Metric | Ý nghĩa |
|---|---|
| `latency` | Thời gian xử lý trung bình cho mỗi câu hỏi. |
| `success_rate` | Tỷ lệ câu hỏi chạy thành công trên tổng số câu hỏi. |
| `context_count` | Số lượng context/evidence trung bình được truy xuất. |
| `scored_samples` | Số mẫu được RAGAS chấm thành công. |
| `error_samples` | Số mẫu lỗi trong quá trình chạy hoặc chấm điểm. |

Các metric này cho phép so sánh các chế độ RAG theo ba khía cạnh:

1. **Mức độ bám bằng chứng**: faithfulness.
2. **Chất lượng truy xuất context**: context precision, context recall, context count.
3. **Chi phí và độ ổn định vận hành**: latency, success rate, error samples.

## 4. Quy trình đánh giá dự kiến

Quy trình đánh giá hỏi đáp gồm ba bước chính.

### Bước 1: Chuẩn bị tập câu hỏi

Từ dữ liệu Markdown đã được làm sạch, hệ thống sử dụng RAGAS để sinh hoặc hỗ trợ xây dựng tập câu hỏi đánh giá. Tập câu hỏi nên bao phủ nhiều loại truy vấn khác nhau, ví dụ:

- câu hỏi mô tả trực tiếp,
- câu hỏi về quan hệ giữa đơn vị và tổ chức,
- câu hỏi về người và chức vụ,
- câu hỏi về chương trình đào tạo,
- câu hỏi multi-hop cần tổng hợp nhiều nguồn.

### Bước 2: Chạy các chế độ RAG

Mỗi câu hỏi được chạy qua các chế độ truy xuất cần so sánh:

| Chế độ | Nguồn bằng chứng chính |
|---|---|
| Semantic Search | Markdown chunks từ Qdrant |
| Naive Graph RAG | Graph context từ Neo4j |
| Graph Search | Graph facts và reasoning steps từ Neo4j |
| Hybrid RAG | Kết hợp markdown chunks và graph evidence |

Kết quả runner cần lưu lại:

- câu hỏi,
- câu trả lời,
- context truy xuất,
- citations hoặc evidence,
- reasoning steps nếu có,
- latency.

### Bước 3: Chấm điểm bằng RAGAS

Sau khi có output từ runner, RAGAS được dùng để tính các metric cho từng câu hỏi và từng chế độ. Kết quả cuối cùng được tổng hợp theo mode trong một bảng như sau:

| Chế độ | Success rate | Latency TB | Faithfulness | Answer correctness | Answer relevancy | Context precision | Context recall |
|---|---:|---:|---:|---:|---:|---:|---:|
| Semantic Search | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Naive Graph RAG | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Graph Search | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Hybrid RAG | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

Bảng này là kết quả chính để phân tích vai trò của Knowledge Graph trong hệ thống hỏi đáp. Trong trường hợp chi phí chấm điểm cao, có thể báo cáo bảng rút gọn chỉ gồm `faithfulness`, `context_precision`, `context_recall` và `latency`, đồng thời ghi rõ các metric chưa được tính.

## 5. Cách diễn giải kết quả

Khi diễn giải kết quả, khóa luận cần thận trọng và tránh kết luận quá mức. Một số nguyên tắc diễn giải:

- Nếu Hybrid RAG có context recall cao hơn Semantic Search, có thể nói graph bổ sung bằng chứng hữu ích khi kết hợp với văn bản.
- Nếu Graph Search hoặc Naive Graph RAG có kết quả thấp, không nên kết luận Knowledge Graph không hữu ích; cần phân tích thêm chất lượng graph, entity linking và khả năng truy xuất graph.
- Nếu latency của Hybrid RAG hoặc Graph Search cao, cần xem đây là trade-off giữa chất lượng truy xuất và chi phí vận hành.
- Không dùng thống kê extraction/ER để khẳng định độ chính xác của hai giai đoạn này.

Luận điểm mong muốn của đánh giá là:

> Knowledge Graph không nhất thiết thay thế semantic retrieval, nhưng có thể phát huy giá trị khi được kết hợp với bằng chứng văn bản trong Hybrid RAG.

## 6. Hạn chế của cách đánh giá

Cách đánh giá hiện tại có một số hạn chế:

- Chưa có ground truth cho extraction và Entity Resolution.
- Tập câu hỏi RAGAS cần đủ đa dạng để đại diện cho miền dữ liệu UET.
- RAGAS sử dụng LLM làm evaluator nên kết quả có thể phụ thuộc vào mô hình đánh giá.
- Các chế độ Graph Search và Hybrid RAG có thể tốn nhiều chi phí do cần nhiều lượt gọi LLM.
- Cần phân tích lỗi thủ công để hiểu rõ nguyên nhân của các điểm số thấp.

## 7. Hướng mở rộng đánh giá

Trong tương lai, có thể mở rộng đánh giá theo các hướng:

- Xây dựng ground truth cho extraction và Entity Resolution.
- Chấm điểm trên tập câu hỏi lớn hơn.
- Phân tích riêng câu hỏi single-hop và multi-hop.
- Phân tích lỗi theo từng nhóm: thiếu context, context nhiễu, graph thiếu quan hệ, entity linking sai, câu trả lời không faithful.
- Bổ sung human evaluation cho một tập mẫu nhỏ để kiểm chứng kết quả RAGAS.
