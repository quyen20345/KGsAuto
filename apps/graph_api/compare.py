import json
import logging
import re

from fastapi import APIRouter
from pydantic import BaseModel, Field

from apps.graph_api.neo4j import get_driver
from services.config import (
    LLM_MODEL,
    LLM_PROVIDER,
    OPENAI_COMPATIBLE_API_KEY,
    OPENAI_COMPATIBLE_BASE_URL,
)
from services.llms import get_llm

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["compare"])


class CompareRequest(BaseModel):
    entity_id_a: str = Field(..., min_length=1)
    entity_id_b: str = Field(..., min_length=1)


class CompareResponse(BaseModel):
    success: bool
    data: dict | None = None
    error: str | None = None


def _fetch_entity(session, entity_id: str) -> dict | None:
    result = session.run(
        """
        MATCH (n) WHERE n.id = $id
        OPTIONAL MATCH (n)-[r_out]->(m_out)
        RETURN n.id AS id, n.name AS name, labels(n) AS labels,
               properties(n) AS properties,
               collect(DISTINCT {type: type(r_out), target_id: m_out.id, target_name: m_out.name}) AS outgoing
        """,
        {"id": entity_id},
    ).single()

    if not result or not result["id"]:
        return None

    return {
        "id": result["id"],
        "name": result["name"],
        "labels": result["labels"],
        "properties": result["properties"] or {},
        "outgoing": [r for r in result["outgoing"] if r.get("target_id")],
    }


def _format_entity(entity: dict) -> str:
    props = entity["properties"]
    aliases = props.get("aliases") or []
    description = props.get("description", "")
    if isinstance(description, list):
        description = "; ".join(str(d) for d in description[:3])
    elif description:
        description = str(description)[:300]

    rels = entity["outgoing"]
    rel_summary = ""
    if rels:
        rel_types = {}
        for r in rels:
            rel_types.setdefault(r["type"], []).append(r.get("target_name") or r["target_id"])
        rel_lines = []
        for rtype, targets in list(rel_types.items())[:5]:
            targets_str = ", ".join(targets[:3])
            if len(targets) > 3:
                targets_str += f" (+{len(targets) - 3} more)"
            rel_lines.append(f"    {rtype} -> {targets_str}")
        rel_summary = "\n".join(rel_lines)

    lines = [
        f"  ID: {entity['id']}",
        f"  Labels: {[l for l in entity['labels'] if l != 'KgNode']}",
        f"  Name: {entity['name'] or 'N/A'}",
    ]
    if aliases:
        lines.append(f"  Aliases: {aliases}")
    if description:
        lines.append(f"  Description: {description}")
    if rel_summary:
        lines.append(f"  Relationships:\n{rel_summary}")

    return "\n".join(lines)


def _build_prompt(entity_a: dict, entity_b: dict) -> str:
    formatted_a = _format_entity(entity_a)
    formatted_b = _format_entity(entity_b)

    return f"""Task: Xác định xem hai entity sau có cùng tham chiếu đến một thực thể trong thế giới thực hay không.

Entity A:
{formatted_a}

Entity B:
{formatted_b}

Yêu cầu: Phân tích từng tiêu chí dưới đây và đưa ra kết luận dựa trên bằng chứng cụ thể.

Checklist bắt buộc:
1. name_match: Tên có giống nhau hoặc là biến thể của nhau không? (bao gồm viết tắt, có/không có tổ chức cha)
2. alias_overlap: Có alias nào của entity A trùng với tên/alias của entity B (hoặc ngược lại) không?
3. label_match: Hai entity có cùng label/loại không?
4. description_contradiction: Có bằng chứng mâu thuẫn không? (khác vai trò, khác địa điểm, khác thời kỳ, khác ngữ cảnh)
5. relationship_overlap: Có relationship chung hoặc tương tự không? (cùng target, cùng loại quan hệ)

Quy tắc quyết định:
- Merge: Cần ít nhất 2 tiêu chí tích cực (name_match, alias_overlap, hoặc relationship_overlap) VÀ không có mâu thuẫn.
- Do not merge: Có mâu thuẫn rõ ràng, HOẶC chỉ có 1 tiêu chí tích cực yếu mà không có bằng chứng bổ sung.

Lưu ý tiếng Việt:
- Nhận diện viết tắt: ĐHCN = Đại học Công nghệ, UET = University of Engineering and Technology, ĐHQGHN = Đại học Quốc gia Hà Nội
- Tên có/không có tổ chức cha (ví dụ "Trường ĐHCN" vs "Trường ĐHCN, ĐHQGHN") thường là cùng một thực thể

Chọn canonical:
- canonical_entity_id: entity có nhiều thông tin hơn (nhiều relationship, description đầy đủ hơn)
- suggested_name: tên đầy đủ và chính thức nhất

Output JSON format:
{{
  "checklist": {{
    "name_match": {{"result": true/false, "detail": "giải thích ngắn"}},
    "alias_overlap": {{"result": true/false, "detail": "giải thích ngắn"}},
    "label_match": {{"result": true/false, "detail": "giải thích ngắn"}},
    "description_contradiction": {{"result": true/false, "detail": "giải thích ngắn"}},
    "relationship_overlap": {{"result": true/false, "detail": "giải thích ngắn"}}
  }},
  "decision": "merge" hoặc "do_not_merge",
  "confidence": <float 0.0-1.0>,
  "reasoning": "<tóm tắt lý do quyết định>",
  "canonical_entity_id": "<id entity giữ lại>",
  "suggested_name": "<tên canonical tốt nhất>"
}}

Return ONLY valid JSON, no markdown, no extra text."""


def _extract_json(raw: str) -> dict | None:
    cleaned = raw.replace("```json", "").replace("```", "").strip()

    if "<think>" in cleaned and "</think>" in cleaned:
        cleaned = cleaned.split("</think>", 1)[1].strip()

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def _validate_response(parsed: dict, entity_a_id: str, entity_b_id: str) -> dict:
    decision = parsed.get("decision", "do_not_merge")
    if decision not in ("merge", "do_not_merge"):
        decision = "do_not_merge"

    confidence = parsed.get("confidence", 0.5)
    if not isinstance(confidence, (int, float)):
        confidence = 0.5
    confidence = max(0.0, min(1.0, float(confidence)))

    canonical_id = parsed.get("canonical_entity_id", entity_a_id)
    if canonical_id not in (entity_a_id, entity_b_id):
        canonical_id = entity_a_id

    checklist = parsed.get("checklist", {})
    validated_checklist = {}
    for key in ("name_match", "alias_overlap", "label_match", "description_contradiction", "relationship_overlap"):
        item = checklist.get(key, {})
        if isinstance(item, dict):
            validated_checklist[key] = {
                "result": bool(item.get("result", False)),
                "detail": str(item.get("detail", "")),
            }
        else:
            validated_checklist[key] = {"result": False, "detail": ""}

    return {
        "checklist": validated_checklist,
        "decision": decision,
        "confidence": confidence,
        "reasoning": parsed.get("reasoning", ""),
        "canonical_entity_id": canonical_id,
        "suggested_name": parsed.get("suggested_name", ""),
        "entity_id_a": entity_a_id,
        "entity_id_b": entity_b_id,
    }


@router.post("/entity/compare", response_model=CompareResponse)
def compare_entities(payload: CompareRequest):
    driver = get_driver()

    with driver.session() as session:
        entity_a = _fetch_entity(session, payload.entity_id_a)
        if not entity_a:
            return {"success": False, "data": None, "error": f"Entity not found: {payload.entity_id_a}"}

        entity_b = _fetch_entity(session, payload.entity_id_b)
        if not entity_b:
            return {"success": False, "data": None, "error": f"Entity not found: {payload.entity_id_b}"}

    prompt = _build_prompt(entity_a, entity_b)

    try:
        llm = get_llm(
            LLM_PROVIDER,
            model_name=LLM_MODEL,
            api_key=OPENAI_COMPATIBLE_API_KEY,
            base_url=OPENAI_COMPATIBLE_BASE_URL,
        )
        response = llm.generate(
            prompt=prompt,
            system_prompt="You are an entity resolution expert. Return only valid JSON.",
        )
        content = response.content if hasattr(response, "content") else str(response)
    except Exception as exc:
        logger.error(f"LLM call failed: {exc}")
        return {"success": False, "data": None, "error": "LLM service unavailable"}

    parsed = _extract_json(content)
    if not parsed:
        logger.warning(f"Failed to parse LLM response: {content[:500]}")
        return {"success": False, "data": None, "error": "Failed to parse LLM response"}

    data = _validate_response(parsed, payload.entity_id_a, payload.entity_id_b)
    return {"success": True, "data": data, "error": None}
