from services.triplet_evaluation.aggregator import aggregate_records


def record(label, predicate="REL", confidence=0.5, valid=True):
    return {
        "triplet": {"relationship": {"predicate": predicate}},
        "judgement": {
            "label": label,
            "confidence": confidence,
            "reason": "reason",
            "valid": valid,
        },
    }


def test_aggregate_records_uses_valid_denominator_and_predicate_breakdown():
    summary = aggregate_records(
        [
            record("supported", "A", 0.8),
            record("not_enough_info", "A", 0.4),
            record("false_verifiable", "B", 0.7),
            record("invalid_response", "B", 0.0, valid=False),
        ]
    )

    assert summary["total"] == 4
    assert summary["valid_total"] == 3
    assert summary["invalid_total"] == 1
    assert summary["counts"]["supported"] == 1
    assert summary["counts"]["contradicted"] == 1
    assert summary["valid_rates"]["supported"] == 1 / 3
    assert summary["micro_supported_rate"] == 1 / 3
    assert summary["supported_rate_ci95"]["method"] == "wilson"
    assert 0 <= summary["supported_rate_ci95"]["low"] <= summary["supported_rate_ci95"]["high"] <= 1
    assert summary["by_predicate"]["A"]["valid_total"] == 2
    assert summary["by_predicate"]["B"]["invalid_total"] == 1


def test_aggregate_records_handles_empty_input():
    summary = aggregate_records([])

    assert summary["total"] == 0
    assert summary["valid_total"] == 0
    assert summary["micro_supported_rate"] == 0.0
