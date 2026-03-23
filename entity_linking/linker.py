# import json
# import logging
# from entity_linking.entity_store import EntityDB
# from llms import get_llm

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from entity_linking.entity_store import EntityDB
from llms import get_llm

logger = logging.getLogger(__name__)


ENTITY_LINK_PROMPT = '''Bạn là một chuyên gia Giải quyết Thực thể (Entity Resolution) cho Đồ thị Tri thức VNU Knowledge Graph.

## NHIỆM VỤ:
So sánh THỰC THỂ GỐC (seed) với danh sách CÁC ỨNG VIÊN (candidates).
Xác định chính xác ứng viên nào là **cùng một thực thể trong thế giới thực** với thực thể gốc.
Nếu có ứng viên trùng lặp, hãy tạo một thực thể mới hợp nhất toàn vẹn thông tin từ seed và các ứng viên đó.

## SCHEMA THAM CHIẾU (Labels & Properties hợp lệ):
Thực thể hợp nhất PHẢI tuân thủ schema sau. KHÔNG được tự bịa label hay property key mới ngoài schema.
- PERSON: name, aliases, title, role, email, phone, birth_date, gender, hometown, research_interests
- ORGANIZATION: name, aliases, org_type, founded_year, website, address, employee_count, student_capacity
- PUBLICATION: name, pub_type, year, publisher, doi, journal_name
- RESEARCH_PROJECT: name, level, start_year, end_year, status, budget
- MAJOR: name, code, degree_level, duration_years
- COURSE: name, code, credits, course_type
- PARTNER: name, partner_type, country, website
- EVENT: name, date, scope
- AWARD: name, issuer, year, prize_money
- FACILITY: name, location, facility_type, capacity

## QUY TẮC QUYẾT ĐỊNH (MATCHING RULES):
1. **CHỈ MERGE KHI CHẮC CHẮN** là cùng một thực thể:
   - Cùng tên hoặc tên là alias/viết tắt của nhau (VD: "Trí tuệ nhân tạo" ↔ "Artificial Intelligence").
   - Cùng ID pattern trùng khớp (VD: `person_nguyen_van_a` ↔ `person_nguyen_van_a_1`).
   - Cùng label VÀ các thuộc tính định danh (name, code, email) khớp nhau.
2. **TUYỆT ĐỐI KHÔNG MERGE khi**:
   - Khác tên định danh cá nhân: "Trần Xuân Tú" vs "Phạm Bảo Sơn" (dù cùng tổ chức).
   - Quan hệ bao hàm/cha-con: "ĐHQGHN" vs "UET" (đây là quan hệ PART_OF, không phải cùng thực thể).
   - Khác label cơ bản: PERSON vs ORGANIZATION, COURSE vs MAJOR.
   - Tương đồng ngữ nghĩa nhưng khác thực thể: "Machine Learning" vs "Deep Learning", "Khoa CNTT" vs "Khoa Điện tử".
3. **Nguyên tắc Thận trọng**: Thiếu ngữ cảnh để khẳng định 100% → KHÔNG MERGE.

## QUY TẮC HỢP NHẤT DỮ LIỆU (MERGING RULES):
Nếu quyết định merge, thực thể `new_entity` PHẢI tuân thủ:
- **id**: Giữ nguyên `id` của THỰC THỂ GỐC (seed). KHÔNG tự tạo ID mới.
- **labels**: Gộp (union) tất cả labels, loại bỏ trùng lặp. CHỈ dùng labels có trong Schema.
- **name**: Chọn tên đầy đủ, chính thức nhất. Đưa mọi tên khác (viết tắt, alias, tên cũ) vào `aliases`.
- **properties**: Gộp tất cả thuộc tính. CHỈ dùng property keys có trong Schema (theo label tương ứng). Giữ lại `source` dưới dạng mảng gộp tất cả nguồn. Nếu xung đột mô tả, kết hợp thành mô tả chi tiết nhất.
- **Phẳng hóa**: Mọi giá trị phải là string, number, boolean hoặc array of strings. KHÔNG object lồng nhau.

## DỮ LIỆU ĐẦU VÀO:
[THỰC THỂ GỐC]:
{seed_json}

[CÁC ỨNG VIÊN]:
{candidates_text}

## OUTPUT FORMAT:
Chỉ trả về MỘT chuỗi JSON hợp lệ duy nhất. KHÔNG bọc markdown, KHÔNG giải thích.
- Nếu CÓ merge:
{{
  "merge_ids": ["<id_ứng_viên_1>", "<id_ứng_viên_2>"],
  "new_entity": {{
    "id": "<id_seed>",
    "labels": ["<label_từ_schema>"],
    "properties": {{
      "name": "<tên đầy đủ nhất>",
      "aliases": ["<tên khác>"],
      "description": "<mô tả tổng hợp>",
      "source": ["<doc_id_1>", "<doc_id_2>"]
    }}
  }}
}}
- Nếu KHÔNG merge:
{{
  "merge_ids": [],
  "new_entity": null
}}
'''


def _format_candidates(candidates: list[dict]) -> str:
    lines = []
    for i, c in enumerate(candidates, 1):
        props = c.get("properties", {})
        lines.append(f"--- Ứng viên {i} (score={c.get('_score', 0):.3f}) ---")
        lines.append(f"  id: {c.get('entity_id', '')}")
        lines.append(f"  labels: {c.get('labels', [])}")
        lines.append(f"  properties: {json.dumps(props, ensure_ascii=False, indent=4)}")
        lines.append("")
    return "\n".join(lines)


def _ask_llm(llm, seed: dict, candidates: list[dict]) -> dict | None:
    """Send seed + candidates to LLM. Returns parsed response or None."""
    seed_json = json.dumps({
        "id": seed.get("entity_id", ""),
        "labels": seed.get("labels", []),
        "properties": seed.get("properties", {}),
    }, ensure_ascii=False, indent=2)

    prompt = ENTITY_LINK_PROMPT.format(
        seed_json=seed_json,
        candidates_text=_format_candidates(candidates),
    )

    response = llm.generate(prompt)
    raw = response.content.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Failed to parse LLM response for seed=%s", seed.get("entity_id"))
        return None


# def entity_link_iteration(store: EntityDB, llm, limit: int = 10, score_threshold: float = 0.8) -> int:
#     """
#     One pass: for each entity → search similar → LLM judges → apply merges.
#     Returns number of merges.
#     """
#     all_ids = store.get_all_entity_ids()
#     merges = 0
#     processed = set()

#     for entity_id in all_ids:
#         if entity_id in processed:
#             continue

#         seed = store.get_entity_by_id(entity_id)
#         if seed is None:
#             continue

#         seed_as_entity = {
#             "id": seed.get("entity_id", ""),
#             "labels": seed.get("labels", []),
#             "properties": seed.get("properties", {}),
#         }

#         candidates = store.search_similar(seed_as_entity, limit=limit, score_threshold=score_threshold)
#         candidates = [c for c in candidates if c.get("entity_id") not in processed]
#         if not candidates:
#             continue

#         result = _ask_llm(llm, seed, candidates)
#         if result is None:
#             continue

#         merge_ids = result.get("merge_ids", [])
#         new_entity = result.get("new_entity")
#         if not merge_ids or not new_entity:
#             continue

#         # Collect all merged_ids history
#         prev_merged = seed.get("merged_ids", [])
#         new_entity["merged_ids"] = list(set(prev_merged + merge_ids))

#         # Apply: upsert new entity, delete merged ones
#         store.upsert_entities([new_entity])
#         store.delete_entities(merge_ids)

#         processed.update(merge_ids)
#         merges += len(merge_ids)
#         logger.info("Merged %s <- %s", entity_id, merge_ids)

#     return merges


# def run_entity_linking(store: EntityDB, llm, max_iterations: int = 5, **kwargs) -> dict:
#     """Run until convergence or max_iterations."""
#     total = 0
#     for i in range(1, max_iterations + 1):
#         n = entity_link_iteration(store, llm, **kwargs)
#         total += n
#         logger.info("Iteration %d: %d merges", i, n)
#         if n == 0:
#             logger.info("Converged after %d iterations.", i)
#             break

#     remaining = len(store.get_all_entity_ids())
#     return {"total_merges": total, "iterations": i, "remaining_entities": remaining}

def _pair_key(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a <= b else (b, a)

def entity_link_iteration(
    store: EntityDB,
    llm,
    limit: int = 10,
    score_threshold: float = 0.85,
    max_workers: int = 8,
    batch_size: int = 256,
) -> int:
    """
    One pass:
    - Load entities by scroll payload (no N+1)
    - Build candidate list with attempted_pairs cache
    - Ask LLM concurrently
    - Apply merges sequentially + log linked entities
    """
    all_entities = [e for e in store.iter_entities(batch_size=batch_size) if e.get("entity_id")]
    processed = set()
    attempted_pairs = set()
    merges = 0

    future_map = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for seed in all_entities:
            seed_id = seed.get("entity_id", "")
            if not seed_id or seed_id in processed:
                continue

            seed_as_entity = {
                "id": seed_id,
                "labels": seed.get("labels", []),
                "properties": seed.get("properties", {}),
            }

            candidates = store.search_similar(seed_as_entity, limit=limit, score_threshold=score_threshold)
            filtered = []
            for c in candidates:
                cid = c.get("entity_id", "")
                if not cid or cid == seed_id or cid in processed:
                    continue

                key = _pair_key(seed_id, cid)
                if key in attempted_pairs:
                    continue
                attempted_pairs.add(key)
                filtered.append(c)

            if not filtered:
                continue

            fut = executor.submit(_ask_llm, llm, seed, filtered)
            future_map[fut] = (seed_id, filtered)

        for fut in as_completed(future_map):
            seed_id, _ = future_map[fut]

            try:
                result = fut.result()
            except Exception:
                logger.exception("LLM call failed for seed=%s", seed_id)
                continue

            if result is None:
                continue

            merge_ids = result.get("merge_ids", [])
            new_entity = result.get("new_entity")
            if not merge_ids or not new_entity:
                continue

            current_seed = store.get_entity_by_id(seed_id)
            if current_seed is None:
                continue

            valid_merge_ids = [
                mid for mid in merge_ids
                if mid and mid != seed_id and store.get_entity_by_id(mid) is not None
            ]
            if not valid_merge_ids:
                continue

            new_entity["id"] = seed_id  # enforce canonical id = seed id
            prev_merged = current_seed.get("merged_ids", [])
            new_entity["merged_ids"] = sorted(set(prev_merged + valid_merge_ids))

            store.upsert_entities([new_entity])
            store.delete_entities(valid_merge_ids)

            processed.add(seed_id)
            processed.update(valid_merge_ids)
            merges += len(valid_merge_ids)

            logger.info("[LINKED] canonical=%s merged=%s", seed_id, valid_merge_ids)

    logger.info(
        "Iteration summary: merges=%d, attempted_pairs=%d, seeds=%d",
        merges, len(attempted_pairs), len(all_entities)
    )
    return merges


def run_entity_linking(store: EntityDB, llm, max_iterations: int = 5, **kwargs) -> dict:
    """Run until convergence or max_iterations."""
    total = 0
    for i in range(1, max_iterations + 1):
        n = entity_link_iteration(store, llm, **kwargs)
        total += n
        logger.info("Iteration %d: %d merges", i, n)
        if n == 0:
            logger.info("Converged after %d iterations.", i)
            break

    remaining = len(store.get_all_entity_ids())
    return {"total_merges": total, "iterations": i, "remaining_entities": remaining}
