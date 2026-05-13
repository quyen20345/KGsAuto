from services.triplet_evaluation.evidence import build_evidence_dicts
from services.triplet_evaluation.input_builder import build_triplet_input_dict
from services.triplet_evaluation.schemas import SampledTriplet


def make_triplet():
    return SampledTriplet(
        subject_id="s1",
        subject_name="Subject",
        subject_label="Entity",
        subject_properties={"description": "Subject evidence", "chunk_id": "chunk-1"},
        predicate="RELATED_TO",
        rel_properties={"description": "Relationship evidence"},
        object_id="o1",
        object_name="Object",
        object_label="Entity",
        object_properties={"summary": "Object evidence"},
    )


def test_build_evidence_dicts_extracts_graph_local_sources():
    evidence = build_evidence_dicts(make_triplet())

    assert {item["source"] for item in evidence} == {
        "subject.properties.description",
        "subject.properties.chunk_id",
        "relationship.properties.description",
        "object.properties.summary",
    }


def test_input_builder_includes_evidence():
    triplet_input = build_triplet_input_dict(make_triplet())

    assert triplet_input["evidence"]
    assert triplet_input["relationship"]["predicate"] == "RELATED_TO"
