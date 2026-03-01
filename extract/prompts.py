# ==========================================
# 1. COMPACT SCHEMA (Giữ nguyên sự tối ưu)
# ==========================================
COMPACT_SCHEMA_STR = """
### 1. ENTITY LABELS (Thực thể & Thuộc tính cốt lõi):
- PERSON: name, aliases, title, role, email, identifiers
- ORGANIZATION: name, aliases, type
- PUBLICATION: name, type, year, publisher, doi
- RESEARCH_TOPIC: name, level, timeframe, status
- EVENT: name, date, scope
- MAJOR: name, code, degree_level
- COURSE: name, code, credits
- EXTERNAL_PARTNER: name, type, country
- FACILITY: name, location, type
- GRANT_FUNDING: name, amount, year
- AWARD: name, issuer

### 2. RELATIONSHIPS (Quy tắc kết nối):
[PERSON] -WORKS_AT, STUDY_AT, ALUMNI_OF, LEADS-> [ORGANIZATION]
[PERSON] -TEACHES, ENROLLED_IN-> [COURSE]
[PERSON] -SUPERVISES-> [PERSON]
[PERSON] -AUTHORED-> [PUBLICATION]
[ORGANIZATION] -PART_OF-> [ORGANIZATION]
[ORGANIZATION] -PROVIDES_MAJOR-> [MAJOR]
[ORGANIZATION] -HOSTS-> [EVENT]
[ORGANIZATION] -PARTNERS_WITH-> [EXTERNAL_PARTNER]
[COURSE] -BELONGS_TO_MAJOR-> [MAJOR]
[COURSE] -PREREQUISITE_FOR-> [COURSE]
[PERSON/ORGANIZATION] -PARTICIPATED_IN-> [RESEARCH_TOPIC/EVENT]
[RESEARCH_TOPIC/PERSON] -FUNDED_BY-> [EXTERNAL_PARTNER/GRANT_FUNDING]
[PERSON/ORGANIZATION/RESEARCH_TOPIC] -RECEIVED_AWARD-> [AWARD]
[ORGANIZATION/EVENT/FACILITY] -LOCATED_IN-> [FACILITY]
"""

# ==========================================
# 2. PROMPT TEMPLATE (Bổ sung tính mở rộng)
# ==========================================
EXTRACTION_PROMPT = '''Bạn là một chuyên gia về Knowledge Graph Engineering.
Nhiệm vụ của bạn là trích xuất thực thể (nodes) và quan hệ (relationships) dưới dạng JSON object dựa trên VĂN BẢN đầu vào.

## VNU GRAPH SCHEMA (BẮT BUỘC TUÂN THỦ LABEL VÀ TYPE)
{schema_str}

## QUY TẮC TRÍCH XUẤT (Logic Rules):
1. **Trọng tâm**: Tập trung vào các thực thể thuộc hệ sinh thái giáo dục, nghiên cứu của Đại học Quốc gia Hà Nội (VNU).
2. **Sự kiện nguyên tử**: Mỗi quan hệ chỉ chứa MỘT kết nối đơn lẻ giữa 2 node.
3. **Giải quyết đồng tham chiếu**: Tuyệt đối không dùng đại từ (nó, ông ấy...). Phải thay bằng tên đầy đủ.
4. **Tính mở rộng (Dynamic Properties)**: Ngoài các thuộc tính cốt lõi trong Schema, nếu bạn phát hiện văn bản có chứa các thông tin cụ thể, có giá trị khác (ví dụ: quê quán, ngân sách, số lượng sinh viên, thành tựu nổi bật...), HÃY TỰ ĐỘNG THÊM các trường này vào "properties". Tên trường (key) phải dùng tiếng Anh, định dạng `snake_case`.

## QUY TẮC CẤU TRÚC (Graph Rules):
1. **Phẳng hóa Properties**: Neo4j không hỗ trợ nested object (object lồng nhau). Mọi giá trị trong "properties" phải là chuỗi (string), số (number) hoặc mảng nguyên thủy (array of strings). KHÔNG tạo dictionary con bên trong properties.
2. **Bằng chứng văn bản**: Mọi node/relationship đều PHẢI có thuộc tính `source` và `span`.
3. **Định dạng ID**: Sinh ID duy nhất, viết thường, có tiền tố. VD: `person_pham_bao_son`.

## OUTPUT FORMAT (Chỉ trả về JSON):
{{
  "nodes": [
    {{
      "id": "node_id",
      "labels": ["LABEL_TỪ_SCHEMA"],
      "properties": {{
        "name": "Tên thực thể",
        "...": "Các thuộc tính cốt lõi từ Schema",
        "dynamic_key_1": "Giá trị trích xuất thêm (nếu có)",
        "dynamic_key_2": "Giá trị trích xuất thêm (nếu có)",
        "source": "{doc_id}",
        "span": "đoạn trích gốc chứa thực thể"
      }}
    }}
  ],
  "relationships": [
    {{
      "id": "rel_id",
      "type": "QUAN_HE_TU_SCHEMA",
      "start_id": "source_node_id",
      "end_id": "target_node_id",
      "properties": {{
        "source": "{doc_id}",
        "span": "đoạn trích gốc",
        "dynamic_rel_key": "Thông tin thêm về quan hệ (VD: năm bắt đầu, trạng thái) nếu có"
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
    """Prompt extracts the triplet with extensible schema."""
    return EXTRACTION_PROMPT.format(
        schema_str=COMPACT_SCHEMA_STR, 
        text=text, 
        doc_id=doc_id
    )