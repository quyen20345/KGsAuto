"""RAGAS scoring for saved RAG evaluation outputs."""

from __future__ import annotations

import math
import os
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

from dotenv import find_dotenv, load_dotenv

from services.rag_system.evaluation.runner import load_dataset, load_jsonl, write_csv, write_jsonl
from services.config import RAGAS_SCORE_MAX_WORKERS


DEFAULT_METRICS = ["faithfulness", "answer_correctness", "answer_relevancy", "context_precision", "context_recall"]
SCORE_FIELDS = [
    "faithfulness",
    "answer_correctness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
    "ragas_score_status",
    "ragas_score_error",
    "ragas_valid_metrics",
    "ragas_invalid_metrics",
]


class RagasUnavailableError(RuntimeError):
    pass


class RagasScoringError(RuntimeError):
    pass


def score_results(
    results_path: str | Path,
    output_path: str | Path,
    metrics: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    _load_environment()
    rows = load_dataset(results_path)
    selected_metrics = list(metrics or DEFAULT_METRICS)
    scored_rows = [_empty_scored_row(row) for row in rows]
    scoreable = []
    scoreable_indexes = []

    for index, row in enumerate(rows):
        reason = _skip_reason(row, selected_metrics)
        if reason:
            scored_rows[index]["ragas_score_status"] = "skipped"
            scored_rows[index]["ragas_score_error"] = reason
            continue
        scoreable.append(row)
        scoreable_indexes.append(index)

    if scoreable:
        try:
            ragas_scores = _score_with_ragas(scoreable, selected_metrics)
        except RagasScoringError as exc:
            for index in scoreable_indexes:
                scored_rows[index]["ragas_score_status"] = "error"
                scored_rows[index]["ragas_score_error"] = str(exc)
        else:
            for index, scores in zip(scoreable_indexes, ragas_scores):
                scored_rows[index].update(scores)
                status, error, valid_metrics, invalid_metrics = _classify_metric_scores(scores, selected_metrics)
                scored_rows[index]["ragas_score_status"] = status
                scored_rows[index]["ragas_score_error"] = error
                scored_rows[index]["ragas_valid_metrics"] = valid_metrics
                scored_rows[index]["ragas_invalid_metrics"] = invalid_metrics

    write_jsonl(output_path, scored_rows)
    write_csv(Path(output_path).with_suffix(".csv"), scored_rows, fieldnames=_fieldnames(scored_rows))
    summary_rows = _summary_rows(summarize_scores(scored_rows))
    if summary_rows:
        write_csv(Path(output_path).with_suffix(".summary.csv"), summary_rows, fieldnames=list(summary_rows[0].keys()))
    return scored_rows


def score_results_incremental(
    results_path: str | Path,
    output_path: str | Path,
    metrics: Sequence[str] | None = None,
    resume: bool = True,
) -> list[dict[str, Any]]:
    """Score rows one-by-one and append each completed row to JSONL immediately."""

    _load_environment()
    rows = load_dataset(results_path)
    selected_metrics = list(metrics or DEFAULT_METRICS)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    existing_rows: list[dict[str, Any]] = []
    completed_keys: set[str] = set()
    if resume and output.exists():
        existing_rows = load_jsonl(output)
        completed_keys = {_row_key(row, index) for index, row in enumerate(existing_rows)}
        mode = "a"
    else:
        mode = "w"

    with output.open(mode, encoding="utf-8") as file:
        for index, row in enumerate(rows):
            key = _row_key(row, index)
            if key in completed_keys:
                continue

            scored_row = _score_single_row(row, selected_metrics)
            file.write(_json_dumps(scored_row) + "\n")
            file.flush()
            existing_rows.append(scored_row)
            completed_keys.add(key)
            print(
                f"[{len(existing_rows)}/{len(rows)}] {scored_row.get('id') or index}: "
                f"{scored_row.get('ragas_score_status')}"
            )

    write_csv(output.with_suffix(".csv"), existing_rows, fieldnames=_fieldnames(existing_rows))
    summary_rows = _summary_rows(summarize_scores(existing_rows))
    if summary_rows:
        write_csv(output.with_suffix(".summary.csv"), summary_rows, fieldnames=list(summary_rows[0].keys()))
    return existing_rows


def _score_single_row(row: dict[str, Any], selected_metrics: Sequence[str]) -> dict[str, Any]:
    scored_row = _empty_scored_row(row)
    reason = _skip_reason(row, selected_metrics)
    if reason:
        scored_row["ragas_score_status"] = "skipped"
        scored_row["ragas_score_error"] = reason
        return scored_row

    try:
        scores = _score_with_ragas([row], selected_metrics)[0]
    except Exception as exc:
        scored_row["ragas_score_status"] = "error"
        scored_row["ragas_score_error"] = str(exc)
        return scored_row

    scored_row.update(scores)
    status, error, valid_metrics, invalid_metrics = _classify_metric_scores(scores, selected_metrics)
    scored_row["ragas_score_status"] = status
    scored_row["ragas_score_error"] = error
    scored_row["ragas_valid_metrics"] = valid_metrics
    scored_row["ragas_invalid_metrics"] = invalid_metrics
    return scored_row


def summarize_scores(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for row in rows:
        mode = str(row.get("mode") or "unknown")
        group = groups.setdefault(
            mode,
            {
                "mode": mode,
                "total_samples": 0,
                "successful_samples": 0,
                "scored_samples": 0,
                "partial_samples": 0,
                "error_samples": 0,
                "skipped_samples": 0,
                "avg_latency_ms": None,
                "avg_faithfulness": None,
                "avg_answer_correctness": None,
                "avg_answer_relevancy": None,
                "avg_context_precision": None,
                "avg_context_recall": None,
                "_latencies": [],
                "_faithfulness": [],
                "_answer_correctness": [],
                "_answer_relevancy": [],
                "_context_precision": [],
                "_context_recall": [],
            },
        )
        group["total_samples"] += 1
        if row.get("status", "ok") == "ok":
            group["successful_samples"] += 1
        score_status = row.get("ragas_score_status")
        if score_status == "scored":
            group["scored_samples"] += 1
        elif score_status == "partial":
            group["partial_samples"] += 1
        elif score_status == "error":
            group["error_samples"] += 1
        elif score_status == "skipped":
            group["skipped_samples"] += 1
        _append_number(group["_latencies"], row.get("latency_ms"))
        _append_number(group["_faithfulness"], row.get("faithfulness"))
        _append_number(group["_answer_correctness"], row.get("answer_correctness"))
        _append_number(group["_answer_relevancy"], row.get("answer_relevancy"))
        _append_number(group["_context_precision"], row.get("context_precision"))
        _append_number(group["_context_recall"], row.get("context_recall"))

    for group in groups.values():
        group["avg_latency_ms"] = _average(group.pop("_latencies"))
        group["avg_faithfulness"] = _average(group.pop("_faithfulness"))
        group["avg_answer_correctness"] = _average(group.pop("_answer_correctness"))
        group["avg_answer_relevancy"] = _average(group.pop("_answer_relevancy"))
        group["avg_context_precision"] = _average(group.pop("_context_precision"))
        group["avg_context_recall"] = _average(group.pop("_context_recall"))
    return groups


def _score_with_ragas(rows: list[dict[str, Any]], metric_names: Sequence[str]) -> list[dict[str, float | None]]:
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import answer_correctness, answer_relevancy, context_precision, context_recall, faithfulness
        from ragas.run_config import RunConfig
    except ImportError as exc:
        raise RagasUnavailableError("RAGAS is not installed. Install it with: pip install '.[ragas]'") from exc

    metric_registry = {
        "faithfulness": faithfulness,
        "answer_correctness": answer_correctness,
        "answer_relevancy": answer_relevancy,
        "context_precision": context_precision,
        "context_recall": context_recall,
    }
    unknown_metrics = [metric for metric in metric_names if metric not in metric_registry]
    if unknown_metrics:
        raise ValueError(f"Unsupported RAGAS metrics: {', '.join(unknown_metrics)}")

    dataset = Dataset.from_list(
        [
            {
                "user_input": str(row.get("question") or ""),
                "response": str(row.get("answer") or ""),
                "retrieved_contexts": _normalize_contexts(row.get("retrieved_contexts") or row.get("contexts")),
                "reference": str(row.get("reference") or ""),
            }
            for row in rows
        ]
    )
    llm = _build_ragas_llm()
    embedding_metrics = {"answer_correctness", "answer_relevancy"}
    embeddings = _build_ragas_embeddings() if any(metric in embedding_metrics for metric in metric_names) else None
    max_workers = RAGAS_SCORE_MAX_WORKERS
    run_config = RunConfig(
        max_workers=max_workers,
        max_retries=10,
        max_wait=120,
        timeout=300,
    )
    try:
        evaluate_kwargs = {
            "metrics": [metric_registry[metric] for metric in metric_names],
            "llm": llm,
            "run_config": run_config,
        }
        if embeddings is not None:
            evaluate_kwargs["embeddings"] = embeddings
        result = evaluate(dataset, **evaluate_kwargs)
    except Exception as exc:
        raise RagasScoringError(
            "RAGAS scoring failed with the configured evaluator "
            f"({type(exc).__name__}: {_safe_error_message(exc)}). "
            "Check OPENAI_API_KEY/OPENAI_BASE_URL/OPENAI_MODEL or OPENAI_COMPATIBLE_* fallback values."
        ) from exc
    dataframe = result.to_pandas()
    scored = []
    for _, scored_row in dataframe.iterrows():
        scored.append({metric: _optional_float(scored_row.get(metric)) for metric in metric_names})
    return scored


def _build_ragas_llm() -> Any:
    config = _resolve_ragas_openai_config()
    try:
        from langchain_openai import ChatOpenAI
        from ragas.llms import LangchainLLMWrapper
    except ImportError as exc:
        raise RagasUnavailableError(
            "RAGAS OpenAI-compatible scoring requires langchain-openai. Install/update with: pip install '.[ragas]' langchain-openai"
        ) from exc

    llm = ChatOpenAI(
        api_key=config["api_key"],
        base_url=config["base_url"],
        model=config["model"],
        temperature=0,
    )
    return LangchainLLMWrapper(llm)


def _build_ragas_embeddings() -> Any:
    try:
        from openai import OpenAI

        from services.rag_system.evaluation.gen_testset import NvidiaEmbeddings
    except ImportError as exc:
        raise RagasUnavailableError(
            "RAGAS NVIDIA embedding scoring requires openai and ragas embeddings support. "
            "Install/update with: pip install '.[ragas]' openai"
        ) from exc

    api_key = _env_first("RAGAS_EMBEDDING_API_KEY", "NVIDIA_API_KEY")
    if not api_key:
        raise RagasScoringError("Missing RAGAS embedding configuration: RAGAS_EMBEDDING_API_KEY or NVIDIA_API_KEY")

    model = _env_first("RAGAS_EMBEDDING_MODEL", "NVIDIA_EMBED_MODEL") or "nvidia/llama-3.2-nemoretriever-300m-embed-v1"
    base_url = _env_first("RAGAS_EMBEDDING_BASE_URL", "NVIDIA_BASE_URL") or "https://integrate.api.nvidia.com/v1"
    delay_seconds = _optional_float(_env_first("RAGAS_EMBEDDING_DELAY_SECONDS")) or 0.1

    client = OpenAI(api_key=api_key, base_url=base_url)
    return NvidiaEmbeddings(client=client, model=model, delay_seconds=delay_seconds)


def _resolve_ragas_openai_config() -> dict[str, str]:
    api_key = _env_first("OPENAI_API_KEY", "OPENAI_COMPATIBLE_API_KEY")
    base_url = _env_first("OPENAI_BASE_URL", "OPENAI_COMPATIBLE_BASE_URL")
    model = _env_first("OPENAI_MODEL", "OPENAI_COMPATIBLE_MODEL")
    missing = []
    if not api_key:
        missing.append("OPENAI_API_KEY or OPENAI_COMPATIBLE_API_KEY")
    if not base_url:
        missing.append("OPENAI_BASE_URL or OPENAI_COMPATIBLE_BASE_URL")
    if not model:
        missing.append("OPENAI_MODEL or OPENAI_COMPATIBLE_MODEL")
    if missing:
        raise RagasScoringError("Missing RAGAS evaluator configuration: " + ", ".join(missing))
    return {"api_key": api_key, "base_url": base_url, "model": model}


def _load_environment() -> None:
    dotenv_path = find_dotenv(usecwd=True)
    load_dotenv(dotenv_path or None)


def _env_first(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def _safe_error_message(exc: Exception) -> str:
    message = str(exc).strip()
    return message or "no details"


def _json_dumps(row: dict[str, Any]) -> str:
    return json.dumps(row, ensure_ascii=False)


def _row_key(row: dict[str, Any], index: int) -> str:
    return str(row.get("id") or f"index:{index}")


def _empty_scored_row(row: dict[str, Any]) -> dict[str, Any]:
    scored = dict(row)
    for field in SCORE_FIELDS:
        scored.setdefault(field, None)
    return scored


def _skip_reason(row: dict[str, Any], metrics: Sequence[str]) -> str | None:
    if row.get("status", "ok") != "ok":
        return row.get("error") or "generation row failed"
    if not row.get("answer"):
        return "missing answer"
    if not (row.get("retrieved_contexts") or row.get("contexts")):
        return "missing contexts"
    reference_required = any(metric in {"answer_correctness", "context_precision", "context_recall"} for metric in metrics)
    if reference_required and not row.get("reference"):
        return "missing reference"
    return None


def _classify_metric_scores(
    scores: dict[str, Any],
    selected_metrics: Sequence[str],
) -> tuple[str, str | None, list[str], list[str]]:
    valid_metrics = [metric for metric in selected_metrics if _valid_metric(scores.get(metric))]
    invalid_metrics = [metric for metric in selected_metrics if metric not in valid_metrics]
    if not invalid_metrics:
        return "scored", None, valid_metrics, invalid_metrics
    if valid_metrics:
        return "partial", "invalid metrics: " + ", ".join(invalid_metrics), valid_metrics, invalid_metrics
    return "error", "no valid metric values returned", valid_metrics, invalid_metrics


def _valid_metric(value: Any) -> bool:
    number = _optional_float(value)
    return number is not None and not math.isnan(number)


def _normalize_contexts(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    return fields


def _summary_rows(summary: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [summary[mode] for mode in sorted(summary)]


def _append_number(values: list[float], value: Any) -> None:
    number = _optional_float(value)
    if number is not None and not math.isnan(number):
        values.append(number)


def _optional_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)
