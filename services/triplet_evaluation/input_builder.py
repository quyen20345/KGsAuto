"""Build full triplet objects for LLM evaluation."""

from typing import Any

from services.triplet_evaluation.evidence import build_evidence_dicts
from services.triplet_evaluation.schemas import SampledTriplet, TripletEvaluationInput


def build_triplet_input(triplet: SampledTriplet) -> TripletEvaluationInput:
    """Convert a sampled Neo4j relationship into the LLM input object."""
    return TripletEvaluationInput(
        subject={
            "id": triplet.subject_id,
            "name": triplet.subject_name,
            "label": triplet.subject_label,
            "properties": triplet.subject_properties,
        },
        relationship={
            "predicate": triplet.predicate,
            "properties": triplet.rel_properties,
        },
        object={
            "id": triplet.object_id,
            "name": triplet.object_name,
            "label": triplet.object_label,
            "properties": triplet.object_properties,
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
