"""Orchestrate triplet sampling, judging, and persistence."""

from pathlib import Path
from typing import Any
from uuid import uuid4

from services.triplet_evaluation.aggregator import aggregate_jsonl, summary_path
from services.triplet_evaluation.input_builder import build_triplet_input_dict
from services.triplet_evaluation.judge import DEFAULT_MODEL, DEFAULT_PROVIDER, create_judge_llm, evaluate_triplet
from services.triplet_evaluation.sampler import sample_triplets, sample_triplets_by_predicate
from services.triplet_evaluation.schemas import TripletEvaluationResult, TripletJudgement
from services.triplet_evaluation.writer import append_result_jsonl, results_path


RANDOM_STRATEGY = "random"
PREDICATE_STRATIFIED_STRATEGY = "predicate_stratified"
VALID_STRATEGIES = (RANDOM_STRATEGY, PREDICATE_STRATIFIED_STRATEGY)


def _sample(
    sample_size: int,
    strategy: str,
    predicates: list[str] | None,
    exclude_predicates: list[str] | None,
    per_predicate_limit: int | None,
):
    if strategy == RANDOM_STRATEGY:
        return sample_triplets(
            sample_size,
            predicates=predicates,
            exclude_predicates=exclude_predicates,
        )
    if strategy == PREDICATE_STRATIFIED_STRATEGY:
        return sample_triplets_by_predicate(
            per_predicate_limit or sample_size,
            predicates=predicates,
            exclude_predicates=exclude_predicates,
        )
    raise ValueError(f"Unknown sampling strategy: {strategy}")


def _invalid_dry_run_judgement() -> TripletJudgement:
    return TripletJudgement(
        label="dry_run",
        confidence=0.0,
        reason="Dry run: judge was not called.",
        raw_response="",
        valid=False,
        error="dry_run",
    )


def run_evaluation(
    sample_size: int = 100,
    output_dir: str | Path = "data/triplet_evaluation",
    provider: str = DEFAULT_PROVIDER,
    model_name: str = DEFAULT_MODEL,
    max_retries: int = 3,
    overwrite: bool = True,
    run_id: str | None = None,
    strategy: str = RANDOM_STRATEGY,
    predicates: list[str] | None = None,
    exclude_predicates: list[str] | None = None,
    per_predicate_limit: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run the full triplet evaluation pipeline."""
    output_path = Path(output_dir)
    result_file = results_path(output_path)
    summary_file = summary_path(output_path)
    resolved_run_id = run_id or uuid4().hex

    if overwrite and result_file.exists():
        result_file.unlink()

    triplets = _sample(
        sample_size=sample_size,
        strategy=strategy,
        predicates=predicates,
        exclude_predicates=exclude_predicates,
        per_predicate_limit=per_predicate_limit,
    )
    llm = None if dry_run else create_judge_llm(provider=provider, model_name=model_name)
    sample_metadata = {
        "strategy": strategy,
        "sample_size": sample_size,
        "predicates": predicates or [],
        "exclude_predicates": exclude_predicates or [],
        "per_predicate_limit": per_predicate_limit,
        "dry_run": dry_run,
    }
    judge_metadata = {
        "provider": provider,
        "model": model_name,
        "max_retries": max_retries,
    }

    for index, sampled_triplet in enumerate(triplets, start=1):
        triplet_input = build_triplet_input_dict(sampled_triplet)
        judgement = (
            _invalid_dry_run_judgement()
            if dry_run
            else evaluate_triplet(
                triplet_input,
                llm=llm,
                provider=provider,
                model_name=model_name,
                max_retries=max_retries,
            )
        )
        result = TripletEvaluationResult(
            id=index,
            run_id=resolved_run_id,
            sample=sample_metadata,
            judge=judge_metadata,
            triplet=triplet_input,
            judgement=judgement,
        )
        append_result_jsonl(result, result_file)
        print(
            f"[{index}/{len(triplets)}] "
            f"{sampled_triplet.predicate}: {judgement.label} ({judgement.confidence:.2f})"
        )

    summary = aggregate_jsonl(result_file, summary_file)
    return {
        "run_id": resolved_run_id,
        "results_file": str(result_file),
        "summary_file": str(summary_file),
        "summary": summary,
    }
