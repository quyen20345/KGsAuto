"""Build full triplet objects for LLM evaluation."""

from typing import Any

from services.triplet_evaluation.evidence import build_evidence_dicts
from services.triplet_evaluation.schemas import SampledTriplet, TripletEvaluationInput


MAX_PROPERTY_ITEMS = 12
MAX_PROPERTY_ITEM_CHARS = 800
MAX_PROPERTY_TEXT_CHARS = 5000


def _truncate_text(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _compact_value(value: Any) -> Any:
    if isinstance(value, str):
        return _truncate_text(value, MAX_PROPERTY_TEXT_CHARS)
    if isinstance(value, list):
        compact = [_compact_value(item) for item in value[:MAX_PROPERTY_ITEMS]]
        if len(value) > MAX_PROPERTY_ITEMS:
            compact.append(f"... ({len(value) - MAX_PROPERTY_ITEMS} more items omitted)")
        return compact
    if isinstance(value, tuple):
        return _compact_value(list(value))
    if isinstance(value, set):
        return _compact_value(sorted(value, key=str))
    if isinstance(value, dict):
        return {str(key): _compact_value(item) for key, item in value.items()}
    return value


def _compact_properties(properties: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key, value in properties.items():
        if key == "model_extracted":
            continue
        if isinstance(value, str):
            compact[key] = _truncate_text(value, MAX_PROPERTY_TEXT_CHARS)
        elif isinstance(value, (list, tuple, set)):
            items = []
            values = list(value) if not isinstance(value, set) else sorted(value, key=str)
            for item in values[:MAX_PROPERTY_ITEMS]:
                if isinstance(item, str):
                    items.append(_truncate_text(item, MAX_PROPERTY_ITEM_CHARS))
                else:
                    items.append(_compact_value(item))
            if len(values) > MAX_PROPERTY_ITEMS:
                items.append(f"... ({len(values) - MAX_PROPERTY_ITEMS} more items omitted)")
            compact[key] = items
        else:
            compact[key] = _compact_value(value)
    return compact


def build_triplet_input(triplet: SampledTriplet) -> TripletEvaluationInput:
    """Convert a sampled Neo4j relationship into the LLM input object."""
    return TripletEvaluationInput(
        subject={
            "id": triplet.subject_id,
            "name": triplet.subject_name,
            "label": triplet.subject_label,
            "properties": _compact_properties(triplet.subject_properties),
        },
        relationship={
            "predicate": triplet.predicate,
            "properties": _compact_properties(triplet.rel_properties),
        },
        object={
            "id": triplet.object_id,
            "name": triplet.object_name,
            "label": triplet.object_label,
            "properties": _compact_properties(triplet.object_properties),
        },
        evidence=build_evidence_dicts(triplet),
    )


def build_triplet_input_dict(triplet: SampledTriplet) -> dict[str, Any]:
    """Convert a sampled triplet to a JSON-serializable LLM input dict."""
    return build_triplet_input(triplet).as_dict()


def build_triplet_inputs(triplets: list[SampledTriplet]) -> list[TripletEvaluationInput]:
    """Convert sampled triplets into LLM input objects."""
    return [build_triplet_input(triplet) for triplet in triplets]


def build_triplet_input_dicts(triplets: list[SampledTriplet]) -> list[dict[str, Any]]:
    """Convert sampled triplets into JSON-serializable LLM input dicts."""
    return [triplet_input.as_dict() for triplet_input in build_triplet_inputs(triplets)]
