import json

# Aligned with extractor schema and ontology.
ENTITY_LABELS = """
UNIVERSITY
ORGANIZATIONAL_UNIT
PERSON
ROLE
STUDY_PROGRAM
COURSE
DEGREE
RESEARCH_PROJECT
PUBLICATION
ADMISSION_METHOD
SCHOLARSHIP
SERVICE
CAMPUS
BUILDING
ROOM
CONTACT_DETAILS
DOCUMENT
ANNOUNCEMENT
"""

MATCH_RULES = """
MERGE khi thoả MỘT trong các điều kiện sau:
1. Cùng thực thể ngoài đời thực theo tên chính thức hoặc biến thể tên/viết tắt/biệt danh được hỗ trợ rõ ràng bởi dữ liệu.
   - Ví dụ: "ĐHBK Hà Nội" ↔ "Đại học Bách Khoa Hà Nội"
   - Ví dụ: "PGS. TS. Nguyễn Văn An" ↔ "Nguyễn Văn An"
2. Cùng mã định danh hoặc thuộc tính định danh duy nhất được nêu rõ.
   - Ví dụ: mã môn học, DOI, ISSN, email cơ quan, mã đề tài, mã chương trình
3. Cùng label và các thuộc tính định danh khớp nhau một cách nhất quán.
   - Ví dụ: cùng `name` + cùng `source_document_id`/bối cảnh đơn vị/cùng mã

KHÔNG MERGE khi:
1. Chỉ giống một phần tên nhưng thiếu bằng chứng rõ ràng là cùng thực thể.
2. Khác thực thể theo quan hệ cha-con hoặc bộ phận.
   - Ví dụ: "Khoa CNTT" và "Đại học Bách Khoa Hà Nội"
3. Cùng tên chung chung nhưng không đủ dấu hiệu định danh.
4. Khác label mà không có bằng chứng rất mạnh cho thấy extractor đã gán nhầm label.
5. Bất kỳ trường hợp nào còn mơ hồ.

NGUYÊN TẮC:
- Ưu tiên precision hơn recall.
- Khi không chắc chắn, KHÔNG merge.
- Chỉ dùng thông tin xuất hiện trong input SEED và CANDIDATE.
- Không suy diễn ngoài dữ liệu được cung cấp.
"""

CANONICAL_MERGE_RULES = """
Khi merge=true, tạo một bộ thuộc tính canonical dùng cho entity store sau linking.
Lưu ý: canonical entity có thể gộp từ nhiều document, nên một số trường phải được nâng từ dạng đơn sang dạng danh sách.

Quy tắc tổng hợp:
- `merged_labels`:
  - Giữ nguyên label nếu SEED và CANDIDATE có cùng label.
  - Union labels nếu khác nhau VÀ có bằng chứng rõ ràng cả hai label đều hợp lệ cho entity này.
  - Không thêm label mới nếu input không hỗ trợ.
  - Trả về mảng, ví dụ: ["PERSON"] hoặc ["PERSON", "ROLE"] nếu có đủ bằng chứng.
- `name`:
  - Chọn tên chính thức, đầy đủ, cụ thể nhất.
  - Không dùng alias làm `name` nếu có tên chính thức rõ ràng hơn.
- `aliases`:
  - Union tất cả biến thể tên, viết tắt, acronym, coreference được hỗ trợ rõ ràng.
  - Loại bỏ trùng lặp.
  - Nếu không có alias thì trả `[]`.
- `source_document_ids`:
  - Union từ `source_document_id` của cả hai entity nếu có.
  - Luôn trả về mảng.
- `models_extracted`:
  - Union từ `model_extracted` của cả hai entity nếu có.
  - Luôn trả về mảng.
- `evidence_texts`:
  - Gom các đoạn bằng chứng ngắn, trực tiếp, hữu ích nhất từ cả hai entity nếu có.
  - Luôn trả về mảng.
- Các thuộc tính domain khác (email, mã số, địa chỉ, v.v.):
  - Chỉ giữ thuộc tính được hỗ trợ rõ ràng bởi input.
  - Ưu tiên giá trị cụ thể hơn, đầy đủ hơn, ít mơ hồ hơn.
  - Không tạo thuộc tính mới nếu dữ liệu không hỗ trợ.

Ràng buộc:
- Không thay đổi bản chất entity.
- Không đổi label chỉ vì suy đoán.
- Không tạo fact mới.
"""

OUTPUT_FORMAT = """
Trả về JSON hợp lệ DUY NHẤT. KHÔNG markdown. KHÔNG giải thích ngoài JSON.

Nếu MERGE:
{
  "evidence_analysis": "<phan tich ngan: bang chung nao ung ho / phan doi viec merge>",
  "merge": true,
  "confidence": <float 0.0-1.0>,
  "reason": "<ly do toi da 1 cau>",
  "merged_labels": ["<label_1>", "<label_2_neu_co>"],
  "merged_properties": {
    "name": "<ten canonical chinh thuc nhat>",
    "aliases": ["<alias_1>", "<alias_2>"],
    "source_document_ids": ["<doc_id_1>", "<doc_id_2>"],
    "models_extracted": ["<model_1>", "<model_2>"],
    "evidence_texts": ["<evidence_1>", "<evidence_2>"],
    "<ten_thuoc_tinh_domain>": "<gia tri tuong ung>"
  }
}

Nếu KHÔNG merge:
{
  "evidence_analysis": "<phan tich ngan: tai sao khong du bang chung de merge>",
  "merge": false,
  "reason": "<ly do toi da 1 cau>"
}
"""

ENTITY_LINK_PROMPT = """\
Bạn là chuyên gia Entity Resolution cho Knowledge Graph đại học.

## NHIỆM VỤ
So sánh SEED entity và CANDIDATE entity.
Xác định xem chúng có đại diện cho cùng MỘT thực thể ngoài đời thực hay không.
Nếu có, trả về dữ liệu canonical đã được hợp nhất để dùng cho entity store sau linking.

## ONTOLOGY / ENTITY LABELS
Phải tôn trọng ontology của extractor dưới đây:
{entity_labels}

## YÊU CẦU QUAN TRỌNG
1. Chỉ sử dụng thông tin có trong SEED và CANDIDATE.
2. Không bịa thêm alias, mã định danh, document id, model name, evidence text hoặc thuộc tính mới.
3. Ưu tiên precision hơn recall: không chắc chắn thì không merge.
4. `merged_properties` là schema canonical sau linking, KHÔNG bắt buộc giống y hệt schema per-document của extractor.
5. Nếu merge, phải bảo toàn provenance:
   - `source_document_id` -> gộp thành `source_document_ids`
   - `model_extracted` -> gộp thành `models_extracted`
   - `evidence_text` -> gộp thành `evidence_texts`
6. Không đổi label trừ khi chính input cho thấy entity đã mang nhiều label hợp lệ. Nếu không cần, giữ nguyên label hiện có.
7. Nếu hai entity khác label và không có bằng chứng rất mạnh rằng đó là cùng một thực thể, trả về `merge=false`.
8. Trước khi quyết định, hãy phân tích bằng chứng trong trường `evidence_analysis` — liệt kê điểm tương đồng và khác biệt cụ thể từ dữ liệu input.

## QUY TẮC NHẬN DẠNG
{match_rules}

## QUY TẮC HỢP NHẤT CANONICAL
{canonical_merge_rules}

## DỮ LIỆU ĐẦU VÀO
[SEED]
{seed_json}

[CANDIDATE]
{candidate_json}

## ĐỊNH DẠNG ĐẦU RA
{output_format}
"""


def _clean(entity: dict) -> dict:
    return {
        "entity_id": entity.get("entity_id") or entity.get("id", ""),
        "labels": entity.get("labels", []),
        "properties": entity.get("properties", {}),
    }


def get_entity_link_prompt(seed: dict, candidate: dict) -> str:
    return ENTITY_LINK_PROMPT.format(
        entity_labels=ENTITY_LABELS,
        match_rules=MATCH_RULES,
        canonical_merge_rules=CANONICAL_MERGE_RULES,
        seed_json=json.dumps(_clean(seed), ensure_ascii=False, indent=2),
        candidate_json=json.dumps(_clean(candidate), ensure_ascii=False, indent=2),
        output_format=OUTPUT_FORMAT,
    )