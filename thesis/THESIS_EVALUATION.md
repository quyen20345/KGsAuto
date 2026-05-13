# Đánh giá thesis hiện tại

Ngày đánh giá: 2026-05-12  
Phạm vi: `/home/quyen/Documents/KGsAuto/thesis/`  
Mục tiêu: đánh giá hiện trạng bản thesis, chỉ ra rủi ro trước khi nộp, và đề xuất thứ tự hành động ưu tiên.

## 1. Executive Summary

Nhìn tổng thể, thesis có nền kỹ thuật khá tốt: pipeline KGsAuto có mạch rõ từ dữ liệu Markdown → trích xuất Knowledge Graph → Entity Resolution → Neo4j/Qdrant → các chế độ RAG → đánh giá RAGAS. Các chương kỹ thuật về extraction, entity resolution và RAG modes đã có nội dung tương đối chắc. Đặc biệt, file `content/chapter7.tex` đã có số liệu thực nghiệm cụ thể và là phần mạnh nhất nếu được đưa vào bản build.

Tuy nhiên, **bản PDF hiện tại chưa sẵn sàng nộp**. Vấn đề nghiêm trọng nhất là `main.tex` đang include `content/chapter7_placeholder` ở `main.tex:217`, trong khi không include `content/chapter7.tex`. Điều này nghĩa là `main.pdf` hiện tại đang dùng Chương 7 placeholder với nhiều `TBD`, “sẽ cập nhật”, và bảng kết quả RAGAS chờ điền, dù đã có một Chương 7 thật chứa kết quả cụ thể.

Nói thẳng: **thesis hiện có nội dung tốt hơn artifact đang build**. Về kỹ thuật LaTeX, PDF hiện tại có vẻ build được, không thiếu hình và không có lỗi log nổi bật. Nhưng về học thuật/nội dung, artifact hiện tại còn trạng thái nháp vì chương thực nghiệm trong PDF chưa phải bản hoàn chỉnh.

Mức đánh giá tổng quan:

- Nội dung kỹ thuật tiềm năng: **Khá tốt**
- Bản PDF hiện tại: **Chưa sẵn sàng nộp**
- Sau khi thay Chương 7 placeholder bằng Chương 7 thật và đồng bộ Abstract/Kết luận: **có thể đạt mức khá**
- Rủi ro lớn nhất khi bảo vệ: Hội đồng thấy Chương 7 còn `TBD` hoặc số liệu extraction/ER không nhất quán.

## 2. Scorecard theo tiêu chí

Thang điểm: 1 = rất yếu, 5 = tốt/sẵn sàng.

| Tiêu chí | Điểm | Nhận xét | Hành động chính |
|---|---:|---|---|
| Tính hoàn chỉnh của bản build hiện tại | 2/5 | `main.pdf` đang dùng `chapter7_placeholder`, còn nhiều `TBD` và “sẽ cập nhật”. | Include `content/chapter7.tex` thay placeholder. |
| Mạch luận tổng thể | 4/5 | Tuy chia 8 chương, thesis vẫn kể được mạch: dữ liệu → KG → ER → RAG → đánh giá. | Làm rõ hơn ở Chương 1 và kết luận. |
| Đóng góp kỹ thuật | 4/5 | Extraction, ER, multi-mode RAG và RAGAS evaluation tạo thành pipeline tương đối đầy đủ. | Nhấn mạnh đóng góp ở Chương 1/8. |
| Đánh giá thực nghiệm | 2/5 trong PDF hiện tại; 4/5 trong `chapter7.tex` | Bản đang build là placeholder; bản thật có số liệu RAGAS và pipeline. | Dùng Chương 7 thật, sửa citation và bất nhất số liệu. |
| Tính nhất quán số liệu | 3/5 | Chương 7 thật có số liệu tốt nhưng extraction batch và ER toàn corpus dễ gây hiểu nhầm. | Giải thích batch mới vs toàn bộ corpus. |
| Tuân thủ `THESIS_RULES.md` | 3/5 | Có đủ phần chính, nhưng thiếu danh mục viết tắt và bibliography style có thể chưa khớp quy định. | Thêm danh mục viết tắt, kiểm tra TLTK. |
| Chất lượng trình bày | 3.5/5 | Build ổn, hình không thiếu; một số chương còn ngắn/lỗi thời. | Đồng bộ Abstract, Chương 8, rà future tense. |
| Sẵn sàng nộp | 2/5 | Chưa nên nộp bản hiện tại. | Xử lý toàn bộ P0 trước. |

## 3. Critical Issues

### P0 — Phải xử lý trước khi nộp

#### P0.1. `main.tex` đang include sai file Chương 7

- Hiện trạng: `main.tex:217` đang dùng:

```tex
\input{content/chapter7_placeholder}
```

- Trong khi đó `content/chapter7.tex` tồn tại và có số liệu cụ thể.
- Tác động: `main.pdf` hiện tại không chứa chương thực nghiệm thật.
- Mức độ: **nghiêm trọng nhất**.
- Hành động: dùng `content/chapter7.tex` làm Chương 7 chính sau khi sửa citation và rà số liệu.

#### P0.2. Chương 7 placeholder còn nhiều dấu hiệu nháp

File: `content/chapter7_placeholder.tex`

Dấu hiệu cụ thể:

- `chapter7_placeholder.tex:6`: “Các kết quả chi tiết sẽ được bổ sung sau...”.
- `chapter7_placeholder.tex:12`: “Các giá trị cụ thể có thể được cập nhật sau...”.
- `chapter7_placeholder.tex:51-64`: nhiều giá trị `TBD` trong bảng extraction.
- `chapter7_placeholder.tex:76-90`: nhiều giá trị `TBD` trong bảng Entity Resolution.
- `chapter7_placeholder.tex:130-147`: bảng RAGAS có toàn `TBD`.
- `chapter7_placeholder.tex:155`: “Phần này sẽ được hoàn thiện sau...”.
- `chapter7_placeholder.tex:159`: “Chương này hiện đóng vai trò là khung thực nghiệm và đánh giá.”

Tác động: nếu Hội đồng đọc bản này, thesis sẽ bị đánh giá là chưa hoàn thiện dù các chương trước có tốt.

#### P0.3. Abstract lỗi thời so với Chương 7 thật

File: `content/abstract.tex`

- `abstract.tex:13` nói hệ thống hỏi đáp “được chuẩn bị để đánh giá bằng khung RAGAS”.
- Nhưng `content/chapter7.tex:219-248` đã có kết quả đánh giá RAGAS cụ thể.

Nếu dùng Chương 7 thật, Abstract cần cập nhật thành: đã đánh giá trên tập pilot 30 câu hỏi, Hybrid RAG đạt faithfulness/context recall tốt nhất, Semantic Search nhanh nhất, graph-only recall thấp.

#### P0.4. Chương 8 lỗi thời so với Chương 7 thật

File: `content/chapter8.tex`

Các câu lỗi thời:

- `chapter8.tex:10`: “Khung đánh giá bằng RAGAS đã được chuẩn bị ở Chương 7...”
- `chapter8.tex:18`: “phần đánh giá hỏi đáp đang được trình bày dưới dạng khung thực nghiệm và bảng kết quả chờ điền.”
- `chapter8.tex:30`: “cần hoàn thiện thực nghiệm RAGAS...”
- `chapter8.tex:42`: “Các kết quả định lượng cuối cùng cần được bổ sung...”

Nếu Chương 7 thật được dùng, Chương 8 phải tổng kết kết quả đã có, không nói như chưa chạy.

#### P0.5. Citation thiếu `es2023ragas` khi dùng Chương 7 thật

- `content/chapter7.tex:197` cite `\cite{es2023ragas}`.
- `sample.bib` hiện chưa có entry này theo khảo sát.
- Vì `chapter7.tex` chưa được include nên build hiện tại chưa lộ warning citation.
- Khi chuyển sang Chương 7 thật, citation này có khả năng thành unresolved citation.

Hành động: bổ sung BibTeX entry cho RAGAS hoặc đổi citation sang key đã có trong `sample.bib`.

### P1 — Nên xử lý để thesis thuyết phục hơn

#### P1.1. Bất nhất số liệu extraction vs Entity Resolution trong Chương 7 thật

File: `content/chapter7.tex`

- `chapter7.tex:92-98`: extraction table ghi 1003 file đầu vào, 47 file thành công, 956 bỏ qua, 514 node, 524 relationship.
- `chapter7.tex:115-119`: ER nhận 1004 KG JSON, tạo 5551 entity records, relationship trước rewiring là 12291.
- `chapter7.tex:270`: tóm tắt nói pipeline extraction xử lý 1003 tài liệu và tạo 514 node/524 relationship.

Vấn đề: người đọc có thể hiểu toàn bộ 1003 tài liệu chỉ tạo 514 node/524 relationship, trong khi ER lại xử lý 5551 entities và 12291 relationships. Có vẻ extraction table đang nói về **batch chạy mới**, còn ER nói về **toàn bộ artifact hiện có**. Cần viết rõ điều này.

Hành động: đổi wording kiểu:

- “Trong batch chạy incremental cuối cùng...” cho bảng extraction 47 success/956 skip.
- Thêm bảng/đoạn “toàn bộ artifact trước ER” nếu có số liệu.
- Không gọi 514/524 là tổng toàn corpus nếu đó chỉ là batch mới.

#### P1.2. Chương 1 quá ngắn so với vai trò mở đầu

File: `content/chapter1.tex`

Điểm có sẵn:

- Bối cảnh và vấn đề: `chapter1.tex:2-8`.
- Mục tiêu và phạm vi: `chapter1.tex:10-18`.
- Cấu trúc khóa luận: `chapter1.tex:20-22`.

Thiếu:

- Câu hỏi nghiên cứu.
- Đóng góp chính của khóa luận.
- Tính cấp thiết tách riêng.
- Phạm vi đánh giá cụ thể hơn, đặc biệt giới hạn ground truth.

Hành động: thêm một section “Đóng góp của khóa luận” và có thể thêm “Câu hỏi nghiên cứu”.

#### P1.3. Chương 2 thiếu Related Work rõ nghĩa

File: `content/chapter2.tex`

Hiện có nền tảng:

- Knowledge Graph và Property Graph: `chapter2.tex:2-30`.
- Ontology: `chapter2.tex:32-38`.
- LLM-based IE: `chapter2.tex:40-48`.
- Entity Resolution: `chapter2.tex:50-58`.
- RAG và Graph-based RAG: `chapter2.tex:60-68`.
- Công nghệ sử dụng: `chapter2.tex:70-80`.

Vấn đề: đây là background tốt nhưng chưa phải “Related Work” đúng nghĩa. Thesis cần cho thấy khác gì so với các hướng đã có: LLM-based KG construction, GraphRAG, Entity Resolution with LLM, RAG evaluation.

Hành động: thêm section Related Work hoặc lồng vào cuối Chương 2.

#### P1.4. Chương 3 thiếu requirement/design rationale

Theo khảo sát, Chương 3 có mạch dữ liệu → yêu cầu → kiến trúc → luồng dữ liệu → model → codebase. Tuy nhiên, phần yêu cầu hệ thống và lý do thiết kế có thể cần chặt hơn.

Hành động:

- Thêm bảng functional/non-functional requirements.
- Thêm mapping requirement → component.
- Nêu rõ vì sao dùng Neo4j, Qdrant, Property Graph, schema-first extraction, multi-mode RAG.

#### P1.5. Chương 5 thiếu giải thích chọn threshold/validation

Chương 5 có pipeline ER rõ và có ngưỡng, nhưng cần giải thích căn cứ chọn ngưỡng/logic fallback.

Hành động:

- Nêu ngưỡng được chọn theo kinh nghiệm/pilot/manual inspection hay heuristic nào.
- Nếu có thể, thêm ví dụ cluster merge đúng/sai.
- Nếu không có ground truth, nói rõ đây là threshold engineering và nêu rủi ro.

#### P1.6. Chương 6 Graph Search cần ví dụ hoặc pseudo-code

File: `content/chapter6.tex`

- Graph Search mô tả ở `chapter6.tex:51-61` khá phức tạp: context preparation, semantic branch, relational branch, Logic Drafter, Evidence Verifier, Query Expander, Final Synthesiser.
- Đây là phần dễ khiến Hội đồng hỏi “flow thực tế chạy thế nào?”.

Hành động:

- Thêm pseudo-code ngắn.
- Hoặc thêm một ví dụ trace: câu hỏi → entity/keyword → graph context → sub-query → evidence → answer.

### P2 — Polish/hình thức

#### P2.1. Thiếu danh mục viết tắt

Thesis dùng nhiều acronym: KG, LLM, RAG, ER, RDF, OWL, JSON, API, Neo4j, Qdrant, RAGAS, LLM judge, HDBSCAN. Theo `THESIS_RULES.md`, danh mục viết tắt là optional nhưng rất nên có nếu dùng nhiều acronym.

#### P2.2. Bibliography style `plain` có thể chưa đúng quy định trường

- `main.tex:225` dùng `\bibliographystyle{plain}`.
- Quy định trong `THESIS_RULES.md` yêu cầu tài liệu tham khảo chia theo ngôn ngữ và xếp ABC theo tác giả.
- `plain` có thể sắp theo tác giả nhưng không tự chia tiếng Việt/tiếng Anh.

Hành động: kiểm với GVHD/khoa. Nếu cần đúng tuyệt đối, phải điều chỉnh bibliography hoặc xử lý thủ công.

#### P2.3. Rà thuật ngữ và future tense

Cần grep/đọc để loại các cụm:

- `TBD`
- `sẽ cập nhật`
- `sẽ được bổ sung`
- `dự kiến`
- `chờ điền`
- `sau khi hoàn tất`

Các cụm này không nên còn trong bản nộp, trừ khi là future work ở Chương 8.

## 4. Chapter-by-chapter review

### Front matter / Abstract

Vai trò: tóm tắt toàn bộ thesis, định vị đóng góp và kết quả chính.

Điểm mạnh:

- Abstract nêu đúng bài toán: LLM/RAG gặp khó với dữ liệu nội bộ và câu hỏi quan hệ (`abstract.tex:9`).
- Tóm tắt được bốn thành phần chính của KGsAuto (`abstract.tex:11`).
- Có từ khóa đầy đủ ở `abstract.tex:17`.

Điểm yếu:

- Lỗi thời nếu dùng Chương 7 thật: `abstract.tex:13` nói RAGAS chỉ được chuẩn bị để đánh giá.
- Chưa nêu kết quả định lượng chính: Hybrid RAG tốt nhất, Semantic Search nhanh nhất, graph-only recall thấp.

Hành động:

- Sau khi quyết định dùng `chapter7.tex`, cập nhật abstract theo số liệu ở `chapter7.tex:231-248`.

### Chương 1 — Mở đầu

Vai trò: đặt bối cảnh, bài toán, mục tiêu, phạm vi và bố cục.

Điểm mạnh:

- Mạch bối cảnh hợp lý: LLM → RAG → dữ liệu nội bộ → hạn chế semantic search → cần KG (`chapter1.tex:4-8`).
- Mục tiêu và phạm vi tương đối rõ (`chapter1.tex:12-18`).
- Nói rõ không xây ontology RDF/OWL hoàn chỉnh và không đề xuất LLM mới (`chapter1.tex:16`).

Điểm yếu:

- Quá ngắn cho một Chương 1.
- Chưa có research questions.
- Chưa có “Đóng góp của khóa luận” tách riêng.
- Đoạn phương pháp ở `chapter1.tex:18` vẫn nói hỏi đáp “được chuẩn bị để đánh giá bằng RAGAS”, cần cập nhật nếu đã có kết quả.

Hành động:

- Thêm section “Câu hỏi nghiên cứu”.
- Thêm section “Đóng góp của khóa luận” với 3–4 bullet.
- Cập nhật trạng thái đánh giá RAGAS.

### Chương 2 — Cơ sở lý thuyết

Vai trò: cung cấp nền tảng KG, extraction, ER, RAG và công nghệ.

Điểm mạnh:

- Bao phủ đúng các khái niệm cần cho thesis.
- Liên kết background với thiết kế KGsAuto, ví dụ Property Graph phù hợp Neo4j (`chapter2.tex:30`).
- Phần ER và Graph-based RAG giải thích đúng động cơ kỹ thuật (`chapter2.tex:52-68`).

Điểm yếu:

- Tiêu đề có dấu chấm: `\chapter{Cơ sở lý thuyết.}` tại `chapter2.tex:0`, hơi không nhất quán.
- Thiếu Related Work rõ nghĩa.
- Phần công nghệ ở `chapter2.tex:70-80` hơi thiên mô tả stack hơn là lý thuyết.

Hành động:

- Thêm/tách Related Work.
- Rà lại tiêu đề chương.
- Nếu cần học thuật hơn, chuyển bớt mô tả công nghệ sang Chương 3.

### Chương 3 — Phân tích bài toán và kiến trúc tổng thể

Vai trò: nối từ bài toán sang thiết kế hệ thống.

Điểm mạnh:

- Mạch chương hợp lý: dữ liệu → yêu cầu → kiến trúc → luồng dữ liệu → model → thành phần code.
- Phù hợp với thesis dạng hệ thống.

Điểm yếu:

- Có thể còn mô tả “hệ thống đang có” nhiều hơn “lý do thiết kế”.
- Thiếu bảng requirement rõ.

Hành động:

- Thêm bảng yêu cầu chức năng/phi chức năng.
- Thêm mapping requirement → component.

### Chương 4 — Trích xuất Knowledge Graph

Vai trò: mô tả phương pháp extraction bằng LLM.

Điểm mạnh:

- Là một trong các chương mạnh.
- Có pipeline, schema, prompt, provenance, validation và limitation.
- Cách viết không overclaim, có nhận diện lỗi extraction trực tiếp bằng LLM.

Điểm yếu:

- Heuristic phân cụm theo tên file cần thêm lý do hoặc ví dụ.
- Nên cross-reference rõ hơn sang số liệu Chương 7.

Hành động:

- Thêm pseudo-code/step-by-step nếu còn thời gian.
- Gắn rõ Chương 4 là methodology, Chương 7 là evaluation/statistics.

### Chương 5 — Entity Resolution

Vai trò: xử lý trùng lặp và hợp nhất thực thể.

Điểm mạnh:

- Pipeline 3 giai đoạn rõ.
- Có tư duy đúng về recall-oriented candidate generation và precision-oriented LLM validation.
- Phần này là đóng góp kỹ thuật đáng kể.

Điểm yếu:

- Chưa đủ căn cứ cho các ngưỡng.
- Thiếu validation định lượng hoặc manual spot-check.

Hành động:

- Thêm bảng stage/input/output.
- Thêm justification ngưỡng và rủi ro under-merge/over-merge.

### Chương 6 — Ứng dụng Knowledge Graph trong hệ thống hỏi đáp

Vai trò: trình bày 4 mode QA/RAG.

Điểm mạnh:

- Bốn chế độ được phân biệt rõ: Semantic Search, Naive Graph RAG, Graph Search, Hybrid RAG.
- Có bảng vai trò thiết kế ở `chapter6.tex:92-109`.
- Có expectation trước thực nghiệm ở `chapter6.tex:111-113`.

Điểm yếu:

- Graph Search ở `chapter6.tex:53-61` nhiều bước, dễ khó hiểu nếu không có ví dụ.
- Chưa có pseudo-code hoặc trace một câu hỏi cụ thể.

Hành động:

- Thêm ví dụ chạy xuyên suốt một câu hỏi.
- Hoặc thêm pseudo-code ngắn cho Graph Search.

### Chương 7 — Placeholder vs bản thật

#### File đang build: `content/chapter7_placeholder.tex`

Đánh giá: không nên dùng để nộp.

Lý do:

- Nhiều `TBD` và “sẽ cập nhật”.
- Bảng RAGAS chưa có số liệu.
- Tóm tắt chương tự nhận là khung thực nghiệm.

#### File nên dùng: `content/chapter7.tex`

Điểm mạnh:

- Có môi trường thực nghiệm (`chapter7.tex:2-41`).
- Có dataset 1003 Markdown, 4.46 triệu ký tự, 100 tài liệu sạch cho RAGAS (`chapter7.tex:43-72`).
- Có số liệu extraction (`chapter7.tex:78-109`).
- Có số liệu ER (`chapter7.tex:111-151`).
- Có phương pháp tạo testset RAGAS (`chapter7.tex:195-217`).
- Có kết quả QA/RAGAS (`chapter7.tex:219-248`).
- Có phân tích trade-off và hạn chế (`chapter7.tex:250-266`).

Điểm yếu:

- Thiếu citation `es2023ragas`.
- Bất nhất hoặc chưa rõ snapshot số liệu extraction vs ER.
- Tập pilot 30 câu hỏi còn nhỏ, dù đã thừa nhận ở `chapter7.tex:262`.

Hành động:

- Chuyển `main.tex` sang include `chapter7.tex`.
- Bổ sung citation.
- Làm rõ số liệu batch/toàn corpus.
- Cập nhật abstract và conclusion theo kết quả này.

### Chương 8 — Kết luận và hướng phát triển

Vai trò: tổng kết đóng góp, hạn chế, hướng phát triển.

Điểm mạnh:

- Có đủ ba phần: kết quả đạt được, hạn chế, hướng phát triển.
- Hạn chế khá trung thực: thiếu ground truth extraction/ER, phụ thuộc graph quality, tổng quát hóa chưa kiểm chứng.

Điểm yếu:

- Lỗi thời so với Chương 7 thật.
- Vẫn nói RAGAS là khung/chờ điền (`chapter8.tex:10`, `chapter8.tex:18`, `chapter8.tex:42`).

Hành động:

- Viết lại phần kết quả hỏi đáp dựa trên số liệu ở `chapter7.tex:231-248`.
- Hạn chế nên nhấn mạnh: tập pilot nhỏ, graph-only recall thấp, Hybrid latency cao, extraction/ER chưa có ground truth.

## 5. Compliance vs `THESIS_RULES.md`

| Yêu cầu/kỳ vọng | Hiện trạng | Mức độ | Hành động |
|---|---|---|---|
| Cấu trúc có mở đầu, lý thuyết, phương pháp, thực nghiệm, kết luận | Có đủ vai trò nhưng chia 8 chương | Chấp nhận được | Giữ 8 chương nếu mạch rõ; giải thích tốt trong Chương 1. |
| Front matter có bìa, phụ bìa, lời cảm ơn, tóm tắt, cam đoan, mục lục, DS hình/bảng | `main.tex:161-183` có các phần này | Khá ổn | Kiểm PDF để xem đánh số front matter. |
| Danh mục viết tắt nếu có nhiều acronym | Chưa thấy include danh mục viết tắt | Thiếu | Bổ sung danh mục viết tắt/thuật ngữ. |
| Chương thực nghiệm có dataset, setup, metrics, kết quả, phân tích | Có trong `chapter7.tex`, chưa có trong PDF hiện tại | Không đạt ở artifact hiện tại | Include Chương 7 thật. |
| Kết luận có kết quả, hạn chế, hướng phát triển | Có, nhưng lỗi thời | Cần sửa | Đồng bộ với Chương 7 thật. |
| TLTK trích dẫn dạng `[n]`, xếp theo quy định | `main.tex:225` dùng `plain`, có thể không chia theo ngôn ngữ | Cần kiểm tra | Kiểm với GVHD/khoa hoặc chỉnh style thủ công. |
| Hình/bảng | Không phát hiện missing images; có danh mục hình/bảng | Khá ổn | Rà caption và nguồn hình nếu hình không tự tạo. |
| Không còn placeholder/TBD | PDF hiện tại còn do include placeholder | Không đạt | Loại placeholder khỏi bản build. |

## 6. Build / artifact checks

Theo khảo sát read-only:

- `main.pdf` tồn tại và có 52 trang.
- Metadata: Creator `LaTeX with hyperref`, Producer `pdfTeX-1.40.25`, page size A4.
- Log build mới nhất không thấy lỗi/warning quan trọng theo grep các pattern phổ biến.
- Không phát hiện missing images trong 16 `\includegraphics`.
- `sample.bib` có 22 entries.
- `main.tex:225-226` include bibliography bằng:

```tex
\bibliographystyle{plain}
\bibliography{sample}
```

Nhận định:

- Về mặt kỹ thuật build, artifact hiện tại có vẻ ổn.
- Về mặt nội dung, artifact hiện tại chưa ổn vì đang build Chương 7 placeholder.
- Khi chuyển sang `content/chapter7.tex`, cần build lại vì có rủi ro citation thiếu `es2023ragas`.

## 7. Prioritized Action Plan

### Trong 1 giờ đầu

1. Đổi Chương 7 được include từ `content/chapter7_placeholder` sang `content/chapter7`.
2. Bổ sung BibTeX entry cho `es2023ragas` hoặc đổi citation sang key đã có.
3. Cập nhật `content/abstract.tex` để phản ánh kết quả RAGAS thật.
4. Cập nhật `content/chapter8.tex` để không còn nói kết quả RAGAS “chờ điền”.
5. Build lại PDF và kiểm log citation/reference.

### Trong nửa ngày

1. Làm rõ số liệu Chương 7: batch extraction mới vs toàn bộ corpus/artifact.
2. Sửa wording ở `chapter7.tex:92-99` và `chapter7.tex:270` để không gây hiểu nhầm.
3. Thêm research questions và contributions vào Chương 1.
4. Bổ sung Related Work ở Chương 2.

### Trong 1–2 ngày

1. Bổ sung requirement/design rationale ở Chương 3.
2. Bổ sung threshold justification/validation ở Chương 5.
3. Thêm pseudo-code hoặc ví dụ trace cho Graph Search ở Chương 6.
4. Bổ sung danh mục viết tắt.
5. Kiểm tra bibliography style theo quy định trường.

### Trước khi nộp

1. Build sạch từ đầu.
2. Grep toàn thesis để chắc không còn `TBD`, `sẽ cập nhật`, `chờ điền`, `placeholder` trong nội dung nộp.
3. Kiểm tra tất cả citations resolved.
4. Kiểm tra TOC, danh mục hình, danh mục bảng.
5. Đọc liền mạch Abstract → Chương 1 → Chương 7 → Chương 8 để đảm bảo thesis kể cùng một câu chuyện.

## 8. Kết luận đánh giá

Thesis này không ở trạng thái “vứt đi”; ngược lại, phần kỹ thuật lõi khá có chất lượng và đã có dữ liệu thực nghiệm đáng dùng trong `content/chapter7.tex`. Nhưng bản build hiện tại đang mắc lỗi tổ chức nghiêm trọng: dùng Chương 7 placeholder thay vì Chương 7 thật. Vì vậy, nếu đánh giá theo nội dung có sẵn trong repo, thesis có tiềm năng khá. Nếu đánh giá theo `main.pdf` hiện tại, thesis chưa sẵn sàng nộp.

Ưu tiên tuyệt đối là đưa đúng Chương 7 thật vào build, đồng bộ Abstract/Kết luận, sửa citation và làm rõ số liệu. Sau nhóm sửa này, thesis sẽ chuyển từ trạng thái “nháp có khung tốt” sang “bản có thể polish để nộp”.
