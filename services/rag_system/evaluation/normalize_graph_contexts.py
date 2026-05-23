"""Normalize saved GraphSearch evaluation contexts for cleaner RAGAS scoring.

This script rewrites existing evaluation outputs without re-running generation:

- contexts/retrieved_contexts keep only retrieval_evidence entries with stage="initial"
- retrieval_evidence is reduced to the same initial entries
- derived_contexts and reasoning_steps are preserved as separate fields
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from services.rag_system.evaluation.runner import load_jsonl, write_csv, write_jsonl


INITIAL_STAGE = "initial"


def _initial_evidence(row: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = row.get("retrieval_evidence") or []
    if not isinstance(evidence, list):
        return []
    return [item for item in evidence if isinstance(item, dict) and item.get("stage") == INITIAL_STAGE]


def _initial_contexts(row: dict[str, Any]) -> list[str]:
    contexts = []
    for item in _initial_evidence(row):
        context = item.get("context")
        if isinstance(context, str) and context.strip():
            contexts.append(context)
    return contexts


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(row)
    initial_evidence = _initial_evidence(row)
    initial_contexts = _initial_contexts(row)

    normalized["contexts"] = initial_contexts
    normalized["retrieved_contexts"] = initial_contexts
    normalized["retrieval_evidence"] = initial_evidence
    normalized["derived_contexts"] = row.get("derived_contexts") or {}
    normalized["reasoning_steps"] = row.get("reasoning_steps")
    normalized["context_count"] = len(initial_contexts)
    normalized.setdefault("metadata", {})
    if isinstance(normalized["metadata"], dict):
        normalized["metadata"] = dict(normalized["metadata"])
        normalized["metadata"]["normalization"] = {
            "retrieved_contexts": "retrieval_evidence[stage == 'initial'].context",
            "retrieval_evidence": "retrieval_evidence[stage == 'initial']",
            "original_context_count": len(row.get("retrieved_contexts") or row.get("contexts") or []),
            "original_retrieval_evidence_count": len(row.get("retrieval_evidence") or []),
        }
    return normalized


def normalize_file(input_path: Path, output_path: Path, write_csv_output: bool = True) -> list[dict[str, Any]]:
    rows = load_jsonl(input_path)
    normalized_rows = [normalize_row(row) for row in rows]
    write_jsonl(output_path, normalized_rows)
    if write_csv_output:
        write_csv(output_path.with_suffix(".csv"), normalized_rows)
    return normalized_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize GraphSearch evaluation contexts.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/evaluation/graph_search.jsonl"),
        help="Input JSONL evaluation file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/evaluation/graph_search.normalized.jsonl"),
        help="Output JSONL path.",
    )
    parser.add_argument("--no-csv", action="store_true", help="Do not write CSV sidecar.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = normalize_file(args.input, args.output, write_csv_output=not args.no_csv)
    with_initial = sum(1 for row in rows if row.get("retrieved_contexts"))
    print(f"Input: {args.input}")
    print(f"Output: {args.output}")
    if not args.no_csv:
        print(f"CSV: {args.output.with_suffix('.csv')}")
    print(f"Rows: {len(rows)}")
    print(f"Rows with initial contexts: {with_initial}")


if __name__ == "__main__":
    main()
