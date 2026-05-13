"""Shared data structures for triplet evaluation."""

from dataclasses import dataclass, field
from typing import Any


RESULT_SCHEMA_VERSION = "triplet_evaluation_result.v2"

SUPPORTED = "supported"
CONTRADICTED = "contradicted"
NOT_ENOUGH_INFO = "not_enough_info"
INVALID_RESPONSE = "invalid_response"
VALID_LABELS = (SUPPORTED, CONTRADICTED, NOT_ENOUGH_INFO)
LEGACY_LABEL_MAP = {
    "true_verifiable": SUPPORTED,
    "non_verifiable": NOT_ENOUGH_INFO,
    "false_verifiable": CONTRADICTED,
}


@dataclass(frozen=True)
class EvidenceItem:
    """Evidence snippet used to judge a sampled triplet."""

    source: str
    text: str

    def as_dict(self) -> dict[str, str]:
        return {
            "source": self.source,
            "text": self.text,
        }


@dataclass(frozen=True)
class SampledTriplet:
    """A relationship sampled from the Neo4j knowledge graph."""

    subject_id: str
    subject_name: str
    subject_label: str | None
    predicate: str
    object_id: str
    object_name: str
    object_label: str | None
    subject_properties: dict[str, Any] = field(default_factory=dict)
    object_properties: dict[str, Any] = field(default_factory=dict)
    rel_properties: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "subject_id": self.subject_id,
            "subject_name": self.subject_name,
            "subject_label": self.subject_label,
            "subject_properties": self.subject_properties,
            "predicate": self.predicate,
            "object_id": self.object_id,
            "object_name": self.object_name,
            "object_label": self.object_label,
            "object_properties": self.object_properties,
            "rel_properties": self.rel_properties,
        }


@dataclass(frozen=True)
class TripletEvaluationInput:
    """Full triplet object sent to the LLM judge."""

    subject: dict[str, Any]
    relationship: dict[str, Any]
    object: dict[str, Any]
    evidence: list[dict[str, str]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "relationship": self.relationship,
            "object": self.object,
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class TripletJudgement:
    """Validated LLM judgement for a triplet."""

    label: str
    confidence: float
    reason: str
    raw_response: str
    evidence_sources: list[str] = field(default_factory=list)
    valid: bool = True
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "confidence": self.confidence,
            "reason": self.reason,
            "evidence_sources": self.evidence_sources,
            "raw_response": self.raw_response,
            "valid": self.valid,
            "error": self.error,
        }


@dataclass(frozen=True)
class TripletEvaluationResult:
    """One persisted evaluation result for a sampled triplet."""

    id: int
    triplet: dict[str, Any]
    judgement: TripletJudgement
    run_id: str
    judge: dict[str, Any]
    sample: dict[str, Any]
    schema_version: str = RESULT_SCHEMA_VERSION

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "id": self.id,
            "sample": self.sample,
            "judge": self.judge,
            "triplet": self.triplet,
            "judgement": self.judgement.as_dict(),
        }
