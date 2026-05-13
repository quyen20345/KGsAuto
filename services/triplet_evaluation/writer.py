"""Persist triplet evaluation results."""

import json
from pathlib import Path
from typing import Any, Iterable

from services.triplet_evaluation.schemas import TripletEvaluationResult


DEFAULT_RESULTS_FILENAME = "evaluated_triplets.jsonl"


def ensure_output_dir(output_dir: str | Path) -> Path:
    """Create and return the output directory path."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def results_path(output_dir: str | Path, filename: str = DEFAULT_RESULTS_FILENAME) -> Path:
    """Return the JSONL results path for an output directory."""
    return ensure_output_dir(output_dir) / filename


def result_to_dict(result: TripletEvaluationResult | dict[str, Any]) -> dict[str, Any]:
    """Convert supported result objects to a JSON-serializable dict."""
    if isinstance(result, TripletEvaluationResult):
        return result.as_dict()
    return result


def append_result_jsonl(
    result: TripletEvaluationResult | dict[str, Any],
    output_file: str | Path,
) -> None:
    """Append one evaluation result to a JSONL file."""
    path = Path(output_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(result_to_dict(result), ensure_ascii=False) + "\n")


def write_results_jsonl(
    results: Iterable[TripletEvaluationResult | dict[str, Any]],
    output_file: str | Path,
) -> None:
    """Write evaluation results to a JSONL file, replacing existing content."""
    path = Path(output_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for result in results:
            file.write(json.dumps(result_to_dict(result), ensure_ascii=False) + "\n")
