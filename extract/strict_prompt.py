# ==========================================
# PRODUCTION PROMPT (Strict Schema + No Span)
# ==========================================
COMPACT_SCHEMA_STR = """
### 1. ENTITY LABELS & EXPECTED PROPERTIES (Chuẩn hóa Thuộc tính):
Mỗi Label dưới đây đi kèm danh sách các thuộc tính tiêu chuẩn. HÃY ƯU TIÊN SỬ DỤNG CÁC KEY NÀY NẾU CÓ THÔNG TIN TRONG VĂN BẢN:

- PERSON: name, aliases, title (học hàm/học vị), role (chức vụ), email, phone, birth_date, gender, hometown, research_interests
- ORGANIZATION: name, aliases, org_type (University, School, Faculty, Department, Lab, Center), founded_year, website, address, employee_count, student_capacity
- PUBLICATION: name (tiêu đề), pub_type (Journal, Conference, Book), year, publisher, doi, journal_name
- RESEARCH_PROJECT: name, level (State, VNU, University), start_year, end_year, status (Ongoing, Completed), budget (kinh phí)
- MAJOR: name, code, degree_level (Bachelor, Master, PhD), duration_years
- COURSE: name, code, credits, course_type (Compulsory, Elective)
- PARTNER: name, partner_type (Academic, Industry, Government), country, website
- EVENT: name, date, scope (International, National, Internal)
- AWARD: name, issuer, year, prize_money
- FACILITY: name, location, facility_type (Campus, Building, Lab, Library), capacity (sức chứa)

### 2. RELATIONSHIPS (TUYỆT ĐỐI CHỈ DÙNG CÁC QUAN HỆ NÀY):
[PERSON] -WORKS_AT, STUDY_AT, ALUMNI_OF, LEADS-> [ORGANIZATION]
[PERSON] -TEACHES, ENROLLED_IN-> [COURSE]
[PERSON] -SUPERVISES-> [PERSON]
[PERSON] -AUTHORED-> [PUBLICATION]
[ORGANIZATION] -PART_OF-> [ORGANIZATION]
[ORGANIZATION] -PROVIDES_MAJOR-> [MAJOR]
[ORGANIZATION] -PARTNERS_WITH-> [PARTNER]
[COURSE] -BELONGS_TO_MAJOR-> [MAJOR]
[COURSE] -PREREQUISITE_FOR-> [COURSE]
[PERSON/ORGANIZATION] -PARTICIPATED_IN-> [RESEARCH_PROJECT/EVENT]
[RESEARCH_PROJECT] -FUNDED_BY-> [PARTNER/ORGANIZATION]
[PERSON/ORGANIZATION/RESEARCH_PROJECT] -RECEIVED_AWARD-> [AWARD]
[ORGANIZATION/EVENT/FACILITY] -LOCATED_IN-> [FACILITY]
"""

# ==========================================
# PROMPT TEMPLATE (Tối ưu Token & Chi phí)
# ==========================================
EXTRACTION_PROMPT = '''Bạn là một chuyên gia Data Engineer xây dựng Knowledge Graph.
Nhiệm vụ của bạn là trích xuất thực thể (nodes) và quan hệ (relationships) dưới dạng JSON object dựa trên VĂN BẢN đầu vào.

## VNU GRAPH SCHEMA (CẤM VI PHẠM)
{schema_str}

## QUY TẮC TRÍCH XUẤT NGHIÊM NGẶT (Strict Rules):
1. **Đóng băng Label/Relationship**: Bạn CHỈ ĐƯỢC PHÉP dùng `labels` và `type` quan hệ có sẵn trong Schema. NẾU không khớp, HÃY BỎ QUA. TUYỆT ĐỐI KHÔNG TỰ BỊA RA LABEL HAY RELATIONSHIP MỚI.
2. **Không ảo giác (Zero Hallucination)**: Chỉ trích xuất những thực thể và thông tin CÓ THẬT trong văn bản. Nếu thông tin không rõ ràng, thà bỏ sót còn hơn trích xuất sai.
3. **Sự kiện nguyên tử**: Mỗi quan hệ chỉ chứa MỘT kết nối đơn lẻ giữa 2 node, tuân thủ đúng chiều mũi tên của Schema.
4. **Giải quyết đồng tham chiếu**: Tuyệt đối không dùng đại từ (nó, ông ấy, trường này...). Phải phân tích ngữ cảnh và thay bằng tên thực thể đầy đủ.

## QUY TẮC THUỘC TÍNH (Property Rules):
1. **Ưu tiên Key Tiêu chuẩn**: Khi trích xuất thuộc tính cho một Node, BẮT BUỘC phải đối chiếu với danh sách "EXPECTED PROPERTIES" trong Schema. 
2. **Thuộc tính động (Fallback)**: CHỈ KHI văn bản chứa thông tin quan trọng nhưng không có key nào trong Schema phù hợp, bạn mới được tạo key mới. Tên key mới bắt buộc là tiếng Anh, định dạng `snake_case`.
3. **Phẳng hóa (Flattening)**: Mọi giá trị trong "properties" phải là chuỗi (string), số (number), boolean hoặc mảng nguyên thủy (array of strings). KHÔNG tạo object lồng nhau.
4. **Thuộc tính quan hệ (Rel Properties)**: Các Relationship cũng có thể có properties (ví dụ: `WORKS_AT` có thể có `start_year`, `role`; `STUDY_AT` có thể có `enrollment_year`).

## QUY TẮC CẤU TRÚC:
1. **Bằng chứng nguồn**: Mọi node/relationship đều PHẢI có thuộc tính `source` mang giá trị `{doc_id}` để lưu vết nguồn gốc tài liệu.
2. **Định dạng ID**: Sinh ID duy nhất, viết thường, loại bỏ dấu tiếng Việt, nối bằng underscore, có tiền tố nhãn. VD: `person_pham_bao_son`, `org_dai_hoc_cong_nghe`.

## OUTPUT FORMAT (Chỉ trả về JSON hợp lệ):
{{
  "nodes": [
    {{
      "id": "node_id",
      "labels": ["CHỈ_CHỌN_TỪ_SCHEMA"],
      "properties": {{
        "name": "Tên chính thức đầy đủ nhất",
        "aliases": ["tên viết tắt", "tên khác"],
        "description": "1 câu mô tả ngắn",
        "...": "Các key tiêu chuẩn ưu tiên lấy từ EXPECTED PROPERTIES",
        "dynamic_key_1": "Giá trị trích xuất thêm (chỉ khi không có key chuẩn)",
        "source": "{doc_id}"
      }}
    }}
  ],
  "relationships": [
    {{
      "id": "rel_id",
      "type": "CHỈ_CHỌN_TỪ_SCHEMA",
      "start_id": "source_node_id",
      "end_id": "target_node_id",
      "properties": {{
        "role": "Thông tin phụ cho quan hệ (ví dụ role, start_year)",
        "source": "{doc_id}"
      }}
    }}
  ]
}}

VĂN BẢN:
---BEGIN---
{text}
---END---
'''

def get_extraction_prompt(text: str, doc_id: str = "doc_001") -> str:
    """Prompt strictly enforces schema with standardized properties and optimized output."""
    return EXTRACTION_PROMPT.format(
        schema_str=COMPACT_SCHEMA_STR, 
        text=text, 
        doc_id=doc_id
    )