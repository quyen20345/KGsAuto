"""Build graph-local evidence for sampled triplets."""

from typing import Any

from services.triplet_evaluation.schemas import EvidenceItem, SampledTriplet


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


def _stringify_evidence_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip()


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
