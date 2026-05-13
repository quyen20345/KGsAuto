"""LLM-based triplet verification judge."""

import json
from typing import Any

from services.config import LLM_MODEL, LLM_PROVIDER, OPENAI_COMPATIBLE_MODEL
from services.llms import BaseLLM, get_llm
from services.triplet_evaluation.schemas import (
    INVALID_RESPONSE,
    LEGACY_LABEL_MAP,
    VALID_LABELS,
    TripletEvaluationInput,
    TripletJudgement,
)


SYSTEM_PROMPT = """You are a strict knowledge graph triplet verification evaluator.
You must return valid JSON only, with no markdown and no extra text."""

DEFAULT_PROVIDER = LLM_PROVIDER or "OpenAICompatible"
DEFAULT_MODEL = OPENAI_COMPATIBLE_MODEL or LLM_MODEL or "deepseek-v4-pro-nothinking"


def build_evaluation_prompt(triplet_input: TripletEvaluationInput | dict[str, Any]) -> str:
    """Build the strict JSON prompt for LLM triplet evaluation."""
    triplet_dict = (
        triplet_input.as_dict()
        if isinstance(triplet_input, TripletEvaluationInput)
        else triplet_input
    )
    triplet_json = json.dumps(triplet_dict, ensure_ascii=False, indent=2)

    return f"""Evaluate whether this knowledge graph triplet is supported by the supplied triplet object and evidence only.

Triplet object:
{triplet_json}

Rules:
1. Use only the subject, relationship, object, properties, and evidence fields in the triplet object.
2. Do not use outside knowledge. A plausible fact is not supported unless the supplied object supports it.
3. Choose supported only when the supplied evidence/context clearly supports the subject-predicate-object triplet.
4. Choose contradicted only when the supplied evidence/context clearly conflicts with the triplet.
5. Choose not_enough_info when evidence is missing, ambiguous, unrelated, or too weak to verify the triplet.
6. When uncertain, choose not_enough_info.

Labels:
- supported: supplied evidence/context supports the triplet.
- contradicted: supplied evidence/context clearly conflicts with the triplet.
- not_enough_info: supplied evidence/context is insufficient to verify the triplet.

Return exactly one JSON object with this schema:
{{
  "label": "supported | contradicted | not_enough_info",
  "confidence": 0.0,
  "reason": "short explanation",
  "evidence_sources": ["source names from the evidence list, or property paths"]
}}
"""


def create_judge_llm(
    provider: str = DEFAULT_PROVIDER,
    model_name: str = DEFAULT_MODEL,
) -> BaseLLM:
    """Create the LLM client used for triplet verification."""
    return get_llm(provider, model_name=model_name)


def generate_judgement_raw(
    triplet_input: TripletEvaluationInput | dict[str, Any],
    llm: BaseLLM | None = None,
    provider: str = DEFAULT_PROVIDER,
    model_name: str = DEFAULT_MODEL,
) -> str:
    """Call the LLM judge and return its raw response content."""
    judge_llm = llm or create_judge_llm(provider=provider, model_name=model_name)
    prompt = build_evaluation_prompt(triplet_input)
    response = judge_llm.generate(prompt, system_prompt=SYSTEM_PROMPT)
    return response.content


def _clean_json_response(raw_response: str) -> str:
    """Remove common markdown fences around JSON responses."""
    cleaned = (raw_response or "").strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned.removeprefix("```json").strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```").strip()
    if cleaned.endswith("```"):
        cleaned = cleaned.removesuffix("```").strip()
    return cleaned


def normalize_label(label: str | None) -> str | None:
    """Return the canonical judgement label for current and legacy labels."""
    if label in VALID_LABELS:
        return label
    return LEGACY_LABEL_MAP.get(str(label))


def _parse_evidence_sources(payload: dict[str, Any]) -> list[str]:
    sources = payload.get("evidence_sources", [])
    if sources is None:
        return []
    if not isinstance(sources, list):
        raise ValueError("evidence_sources must be a list")
    return [str(source) for source in sources]


def parse_judgement(raw_response: str) -> TripletJudgement:
    """Parse and validate the LLM judgement JSON."""
    cleaned = _clean_json_response(raw_response)
    payload = json.loads(cleaned)
    if not isinstance(payload, dict):
        raise ValueError("LLM response must be a JSON object")

    label = normalize_label(payload.get("label"))
    if label not in VALID_LABELS:
        raise ValueError(f"Invalid label: {payload.get('label')}")

    confidence = float(payload.get("confidence"))
    if confidence < 0 or confidence > 1:
        raise ValueError(f"Invalid confidence: {confidence}")

    reason = payload.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("reason must be a non-empty string")

    return TripletJudgement(
        label=label,
        confidence=confidence,
        reason=reason.strip(),
        evidence_sources=_parse_evidence_sources(payload),
        raw_response=raw_response,
    )


def evaluate_triplet(
    triplet_input: TripletEvaluationInput | dict[str, Any],
    llm: BaseLLM | None = None,
    provider: str = DEFAULT_PROVIDER,
    model_name: str = DEFAULT_MODEL,
    max_retries: int = 3,
) -> TripletJudgement:
    """Call the LLM judge and return a validated judgement."""
    judge_llm = llm or create_judge_llm(provider=provider, model_name=model_name)
    last_raw = ""
    last_error = ""

    for _ in range(max_retries):
        last_raw = generate_judgement_raw(
            triplet_input,
            llm=judge_llm,
            provider=provider,
            model_name=model_name,
        )
        try:
            return parse_judgement(last_raw)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            last_error = str(exc)

    return TripletJudgement(
        label=INVALID_RESPONSE,
        confidence=0.0,
        reason="LLM response could not be parsed or validated.",
        raw_response=last_raw,
        valid=False,
        error=last_error,
    )
