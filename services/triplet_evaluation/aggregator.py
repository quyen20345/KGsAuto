"""Aggregate triplet evaluation outputs into summary metrics."""

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from services.triplet_evaluation.judge import normalize_label
from services.triplet_evaluation.schemas import INVALID_RESPONSE, VALID_LABELS


SUMMARY_FILENAME = "summary.json"


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """Load triplet evaluation results from a JSONL file."""
    records: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if stripped:
                records.append(json.loads(stripped))
    return records


def _empty_label_counts() -> dict[str, int]:
    labels = list(VALID_LABELS) + [INVALID_RESPONSE]
    return dict.fromkeys(labels, 0)


def _rates(counts: dict[str, int], total: int) -> dict[str, float]:
    if total == 0:
        return {label: 0.0 for label in counts}
    return {label: count / total for label, count in counts.items()}


def _predicate(record: dict[str, Any]) -> str:
    relationship = record.get("triplet", {}).get("relationship", {})
    predicate = relationship.get("predicate")
    return str(predicate or "UNKNOWN")


def _judgement(record: dict[str, Any]) -> dict[str, Any]:
    judgement = record.get("judgement", {})
    return judgement if isinstance(judgement, dict) else {}


def _canonical_label(judgement: dict[str, Any]) -> str:
    if judgement.get("valid") is False:
        return INVALID_RESPONSE
    return normalize_label(judgement.get("label")) or INVALID_RESPONSE


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _confidence(judgement: dict[str, Any]) -> float | None:
    try:
        value = float(judgement.get("confidence"))
    except (TypeError, ValueError):
        return None
    if value < 0 or value > 1:
        return None
    return value


def _breakdown(counts: Counter[str], confidences: dict[str, list[float]]) -> dict[str, Any]:
    counts_dict = _empty_label_counts()
    counts_dict.update(dict(counts))
    valid_total = sum(counts_dict[label] for label in VALID_LABELS)
    total = valid_total + counts_dict[INVALID_RESPONSE]
    return {
        "total": total,
        "valid_total": valid_total,
        "invalid_total": counts_dict[INVALID_RESPONSE],
        "counts": counts_dict,
        "rates": _rates(counts_dict, total),
        "valid_rates": _rates({label: counts_dict[label] for label in VALID_LABELS}, valid_total),
        "mean_confidence": _mean([value for values in confidences.values() for value in values]),
        "mean_confidence_by_label": {
            label: _mean(confidences.get(label, [])) for label in VALID_LABELS
        },
    }


def aggregate_records(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate evaluation records into summary metrics."""
    record_list = list(records)
    label_counts: Counter[str] = Counter()
    label_confidences: dict[str, list[float]] = defaultdict(list)
    predicate_counts: dict[str, Counter[str]] = defaultdict(Counter)
    predicate_confidences: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    for record in record_list:
        judgement = _judgement(record)
        label = _canonical_label(judgement)
        confidence = _confidence(judgement)
        predicate = _predicate(record)

        label_counts[label] += 1
        predicate_counts[predicate][label] += 1
        if label in VALID_LABELS and confidence is not None:
            label_confidences[label].append(confidence)
            predicate_confidences[predicate][label].append(confidence)

    overall = _breakdown(label_counts, label_confidences)
    by_predicate = {
        predicate: _breakdown(counts, predicate_confidences[predicate])
        for predicate, counts in sorted(predicate_counts.items())
    }
    predicate_supported_rates = [
        data["valid_rates"].get("supported", 0.0)
        for data in by_predicate.values()
        if data["valid_total"] > 0
    ]

    return {
        **overall,
        "micro_supported_rate": overall["valid_rates"].get("supported", 0.0),
        "macro_supported_rate_by_predicate": _mean(predicate_supported_rates),
        "by_predicate": by_predicate,
    }


def write_summary(summary: dict[str, Any], output_file: str | Path) -> None:
    """Write summary metrics as JSON."""
    path = Path(output_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)


def aggregate_jsonl(results_file: str | Path, summary_file: str | Path) -> dict[str, Any]:
    """Aggregate a JSONL result file and write a summary JSON file."""
    summary = aggregate_records(load_jsonl(results_file))
    write_summary(summary, summary_file)
    return summary


def summary_path(output_dir: str | Path, filename: str = SUMMARY_FILENAME) -> Path:
    """Return the summary file path for an output directory."""
    return Path(output_dir) / filename
