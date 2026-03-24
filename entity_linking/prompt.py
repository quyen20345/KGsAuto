ENTITY_LINK_PROMPT = """\
Bạn là chuyên gia Entity Resolution cho VNU Knowledge Graph.

## NHIỆM VỤ
So sánh THỰC THỂ GỐC (seed) với các ỨNG VIÊN (candidates).
Xác định ứng viên nào là **cùng một thực thể trong thế giới thực** với seed.
Nếu có, tạo thực thể hợp nhất từ seed + các ứng viên đó, bao gồm đầy đủ lifecycle metadata.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## QUY TẮC MATCHING

### M1 · Bằng chứng cứng (PHẢI có ít nhất 1 để merge)
  - Tên trùng hoặc là alias/viết tắt của nhau
      VD: "Trí tuệ nhân tạo" ↔ "Artificial Intelligence" ↔ "AI"
  - ID pattern khớp: `university_uet` ↔ `university_uet_1`
  - Thuộc tính định danh khớp: code, email, doi, official abbreviation

### M2 · Tuyệt đối KHÔNG merge khi
  - Tên định danh cá nhân khác nhau: "Trần Xuân Tú" ≠ "Phạm Bảo Sơn"
  - Quan hệ cha-con/bao hàm: "ĐHQGHN" ⊃ "UET" → là PART_OF, không phải SAME_AS
  - Khác label cơ bản: PERSON ≠ ORGANIZATION, COURSE ≠ MAJOR
  - Tương đồng ngữ nghĩa nhưng khác thực thể: "ML" ≠ "Deep Learning"
  - Không đủ bằng chứng cứng → KHÔNG merge (nguyên tắc thận trọng)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## QUY TẮC HỢP NHẤT (khi có merge)

### Data merge
  id         : Giữ nguyên ID của SEED.
  labels     : Union tất cả labels, loại bỏ trùng lặp.
  name       : Chọn tên đầy đủ, chính thức nhất.
  aliases    : Gộp tất cả tên còn lại (seed + mọi candidate được merge).
  source     : Gộp thành array, loại bỏ trùng lặp.
  properties : Gộp tất cả keys. Xung đột → giữ giá trị đầy đủ hơn.
               Mọi value: string | number | boolean | array. KHÔNG object lồng nhau.

### Lifecycle — new_entity (canonical node sau merge)
  status       : Luôn là "active".
  version      : Lấy version hiện tại của seed (trường `_current_version` trong seed)
                 rồi cộng thêm 1.
  absorbed_ids : Gộp `_existing_absorbed_ids` của seed (nếu có) + merge_ids mới.
                 Loại bỏ trùng lặp, sắp xếp tăng dần.
  merge_history: Giữ nguyên `_existing_merge_history` của seed (nếu có),
                 sau đó APPEND thêm một event mới vào cuối:
                 {{
                   "event_id":   "__INJECT__",   ← giữ nguyên chuỗi này, code sẽ thay
                   "merged_at":  "__INJECT__",   ← giữ nguyên chuỗi này, code sẽ thay
                   "absorbed":   ["<id_1>", "<id_2>"],   ← điền các merge_ids
                   "reason":     "<string>",     ← lý do bạn quyết định merge
                   "confidence": <0.0–1.0>,      ← độ chắc chắn của quyết định
                   "notes":      "<string|null>"  ← ghi chú thêm nếu cần
                 }}

### Lifecycle — ghost_updates (các node bị hấp thụ)
  Với mỗi ID trong merge_ids, tạo một ghost record:
  {{
    "id":     "<absorbed_id>",
    "status": "merged",
    "merged_into":  "<seed_id>",
    "updated_at":   "__INJECT__"   ← giữ nguyên chuỗi này, code sẽ thay
  }}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## DỮ LIỆU

[SEED]:
{seed_json}

[CANDIDATES]:
{candidates_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## OUTPUT
Chỉ trả về JSON hợp lệ duy nhất. KHÔNG markdown. KHÔNG giải thích.

Nếu CÓ merge:
{{
  "merge_ids": ["<candidate_id_1>"],
  "new_entity": {{
    "id": "<seed_id>",
    "labels": ["<LABEL>"],
    "properties": {{
      "name":          "<tên đầy đủ nhất>",
      "aliases":       ["<alias_1>", "<alias_2>"],
      "source":        ["<doc_id_1>", "<doc_id_2>"],
      "status":        "active",
      "version":       <int>,
      "absorbed_ids":  ["<id_1>", "<id_2>"],
      "merge_history": [
        // ... giữ nguyên history cũ (nếu có) ...
        {{
          "event_id":   "__INJECT__",
          "merged_at":  "__INJECT__",
          "absorbed":   ["<id_1>"],
          "reason":     "<lý do merge>",
          "confidence": <0.0–1.0>,
          "notes":      "<null hoặc ghi chú>"
        }}
      ]
    }}
  }},
  "ghost_updates": [
    {{
      "id":          "<absorbed_id>",
      "status":      "merged",
      "merged_into": "<seed_id>",
      "updated_at":  "__INJECT__"
    }}
  ]
}}

Nếu KHÔNG merge:
{{
  "merge_ids":   [],
  "new_entity":  null,
  "ghost_updates": []
}}
"""