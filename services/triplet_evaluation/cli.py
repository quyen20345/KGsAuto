"""Command-line entry point for triplet evaluation."""

import argparse
import json

from services.triplet_evaluation.evaluator import RANDOM_STRATEGY, VALID_STRATEGIES, run_evaluation
from services.triplet_evaluation.judge import DEFAULT_MODEL, DEFAULT_PROVIDER


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(description="Evaluate random Neo4j triplets with an LLM judge.")
    parser.add_argument("--sample-size", type=int, default=100, help="Number of triplets to sample.")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/triplet_evaluation",
        help="Directory for evaluated_triplets.jsonl and summary.json.",
    )
    parser.add_argument("--provider", type=str, default=DEFAULT_PROVIDER, help="LLM provider name.")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="LLM model name.")
    parser.add_argument("--max-retries", type=int, default=3, help="Max retries for invalid LLM JSON.")
    parser.add_argument("--run-id", type=str, default=None, help="Optional run identifier stored in outputs.")
    parser.add_argument(
        "--strategy",
        choices=VALID_STRATEGIES,
        default=RANDOM_STRATEGY,
        help="Triplet sampling strategy.",
    )
    parser.add_argument(
        "--predicate",
        action="append",
        default=None,
        help="Relationship type to include. Can be passed multiple times.",
    )
    parser.add_argument(
        "--exclude-predicate",
        action="append",
        default=None,
        help="Relationship type to exclude. Can be passed multiple times.",
    )
    parser.add_argument(
        "--per-predicate-limit",
        type=int,
        default=None,
        help="Maximum samples per predicate for predicate_stratified strategy.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write sampled judge inputs without calling the LLM judge.",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append to existing evaluated_triplets.jsonl instead of replacing it.",
    )
    return parser


def main() -> None:
    """Run triplet evaluation from the command line."""
    args = build_parser().parse_args()
    result = run_evaluation(
        sample_size=args.sample_size,
        output_dir=args.output_dir,
        provider=args.provider,
        model_name=args.model,
        max_retries=args.max_retries,
        overwrite=not args.append,
        run_id=args.run_id,
        strategy=args.strategy,
        predicates=args.predicate,
        exclude_predicates=args.exclude_predicate,
        per_predicate_limit=args.per_predicate_limit,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
