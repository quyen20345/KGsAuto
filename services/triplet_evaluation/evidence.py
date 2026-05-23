"""Build graph-local evidence for sampled triplets."""

from typing import Any

from services.triplet_evaluation.schemas import EvidenceItem, SampledTriplet


MAX_EVIDENCE_ITEMS = 8
MAX_EVIDENCE_ITEM_CHARS = 600
MAX_EVIDENCE_TEXT_CHARS = 4000


EVIDENCE_FIELDS = (
    "description",
    "text",
    "summary",
    "source",
    "sources",
    "chunk_id",
    "doc_id",
    "document_id",
    "url",
    "urls",
)


def _truncate_text(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _stringify_evidence_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return _truncate_text(value, MAX_EVIDENCE_TEXT_CHARS)
    if isinstance(value, (list, tuple, set)):
        items = [
            _truncate_text(str(item), MAX_EVIDENCE_ITEM_CHARS)
            for item in list(value)[:MAX_EVIDENCE_ITEMS]
            if str(item).strip()
        ]
        if len(value) > MAX_EVIDENCE_ITEMS:
            items.append(f"... ({len(value) - MAX_EVIDENCE_ITEMS} more items omitted)")
        return _truncate_text(", ".join(items), MAX_EVIDENCE_TEXT_CHARS)
    return _truncate_text(str(value), MAX_EVIDENCE_TEXT_CHARS)


def _items_from_properties(prefix: str, properties: dict[str, Any]) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    for field in EVIDENCE_FIELDS:
        text = _stringify_evidence_value(properties.get(field))
        if text:
            items.append(EvidenceItem(source=f"{prefix}.properties.{field}", text=text))
    return items


def build_evidence(triplet: SampledTriplet) -> list[EvidenceItem]:
    """Build evidence snippets from graph-local node and relationship properties."""
    return [
        *_items_from_properties("subject", triplet.subject_properties),
        *_items_from_properties("relationship", triplet.rel_properties),
        *_items_from_properties("object", triplet.object_properties),
    ]


def build_evidence_dicts(triplet: SampledTriplet) -> list[dict[str, str]]:
    """Build JSON-serializable evidence snippets."""
    return [item.as_dict() for item in build_evidence(triplet)]
