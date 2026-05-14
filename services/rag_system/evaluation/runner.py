"""Minimal RAG evaluation runner."""

from __future__ import annotations

import csv
import json
import sys
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

from services.rag_system.config import RAGConfig
from services.rag_system.pipeline import UnifiedRetrievalPipeline


csv.field_size_limit(sys.maxsize)


@dataclass
class EvaluationSample:
    id: str
    question: str
    reference: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationResult:
    id: str
    question: str
    reference: str
    mode: str
    answer: str
    contexts: list[str]
    retrieved_contexts: list[str]
    retrieval_evidence: Any
    derived_contexts: dict[str, Any]
    reasoning_steps: Any
    citations: list[str]
    latency_ms: float | None
    retrieval_time_ms: float | None
    synthesis_time_ms: float | None
    token_usage: Any
    effective_top_k_markdown: int | None
    effective_top_k_graph: int | None
    retrieved_markdown_count: int | None
    retrieved_graph_count: int | None
    dropped_context_count: int
    invalid_citations: list[str]
    tags: list[str]
    top_k: int
    context_count: int
    status: str
    error: str | None
    metadata: dict[str, Any]


RESULT_FIELDNAMES = [
    "id",
    "question",
    "reference",
    "mode",
    "answer",
    "contexts",
    "retrieved_contexts",
    "retrieval_evidence",
    "derived_contexts",
    "reasoning_steps",
    "citations",
    "latency_ms",
    "retrieval_time_ms",
    "synthesis_time_ms",
    "token_usage",
    "effective_top_k_markdown",
    "effective_top_k_graph",
    "retrieved_markdown_count",
    "retrieved_graph_count",
    "dropped_context_count",
    "invalid_citations",
    "tags",
    "top_k",
    "context_count",
    "status",
    "error",
    "metadata",
]


ALL_MODES = ["semantic_search", "graph_search", "naive_grag", "hybrid"]
INITIAL_STAGE = "initial"
DERIVED_CONTEXT_KEYS = ("text_summary", "kg_summary")
PROVIDER_ERROR_MARKERS = (
    "OpenAICompatible Error",
    "Error code: 429",
    "rate_limit_exceeded",
    "[429]",
)


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_csv(path: str | Path) -> list[dict[str, Any]]:
    rows = []
    with Path(path).open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for key in (
                "contexts",
                "retrieved_contexts",
                "retrieval_evidence",
                "derived_contexts",
                "reasoning_steps",
                "citations",
                "tags",
                "metadata",
            ):
                if key in row:
                    row[key] = _parse_json_cell(row[key])
            rows.append(row)
    return rows


def _parse_json_cell(value: Any) -> Any:
    if not isinstance(value, str) or not value.strip():
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def load_dataset(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if path.suffix.lower() == ".csv":
        return load_csv(path)
    return load_jsonl(path)


def write_jsonl(path: str | Path, rows: Iterable[dict[str, Any]]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: str | Path, rows: Iterable[dict[str, Any]], fieldnames: Sequence[str] | None = None) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(fieldnames or RESULT_FIELDNAMES)
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            csv_row = {key: row.get(key) for key in fields}
            for key in ("contexts", "retrieved_contexts", "retrieval_evidence", "citations", "tags", "metadata", "derived_contexts", "reasoning_steps"):
                if key in csv_row:
                    csv_row[key] = json.dumps(csv_row.get(key) or _empty_json_value(key), ensure_ascii=False)
            writer.writerow(csv_row)


def _empty_json_value(key: str) -> Any:
    return [] if key in {"contexts", "retrieved_contexts", "retrieval_evidence", "citations", "tags"} else {}


def parse_sample(row: dict[str, Any]) -> EvaluationSample:
    question = str(row.get("user_input") or row.get("question") or "")
    sample_id = str(row.get("id") or uuid.uuid4())
    reference = str(row.get("reference") or "")

    tags = list(row.get("tags") or [])
    if row.get("synthesizer_name"):
        tags.append(str(row["synthesizer_name"]))
    if row.get("persona_name"):
        tags.append(str(row["persona_name"]))

    metadata = dict(row.get("metadata") or {})
    for k, v in row.items():
        if k not in ["id", "question", "user_input", "reference", "tags", "metadata"]:
            metadata[k] = v

    return EvaluationSample(
        id=sample_id,
        question=question,
        reference=reference,
        tags=tags,
        metadata=metadata,
    )


def extract_contexts(response: dict[str, Any]) -> list[str]:
    return extract_retrieved_contexts(response)


def extract_retrieved_contexts(response: dict[str, Any]) -> list[str]:
    initial_contexts = _initial_contexts_from_retrieved_evidence(response.get("retrieved_evidence"))
    if initial_contexts:
        return initial_contexts

    retrieved_from_response = _contexts_from_retrieved_evidence(response.get("retrieved_evidence"))
    if retrieved_from_response:
        return retrieved_from_response

    evidence = response.get("evidence") or {}
    contexts: list[str] = []

    for chunk in evidence.get("markdown_chunks") or []:
        text = _first_text(chunk, "text", "content")
        if text:
            contexts.append(text)

    for fact in evidence.get("graph_facts") or []:
        text = _first_text(fact, "fact_text", "description", "text")
        if text:
            contexts.append(text)

    merged_context = evidence.get("merged_context")
    if isinstance(merged_context, str) and merged_context.strip():
        contexts.append(merged_context.strip())

    graph_context = evidence.get("graph_context")
    if isinstance(graph_context, str) and graph_context.strip():
        contexts.append(graph_context.strip())
    elif isinstance(graph_context, list):
        for item in graph_context:
            text = _first_text(item, "fact_text", "description", "text", "content")
            if text:
                contexts.append(text)
    elif isinstance(graph_context, dict):
        for key in ("initial_context", "context"):
            value = graph_context.get(key)
            if isinstance(value, str) and value.strip():
                contexts.append(value.strip())

    return contexts


def extract_derived_contexts(response: dict[str, Any]) -> dict[str, Any]:
    derived: dict[str, Any] = {}
    response_derived = response.get("derived_evidence")
    if isinstance(response_derived, dict):
        _copy_summary_keys(derived, response_derived)
        graph_derived = response_derived.get("graph_derived")
        if isinstance(graph_derived, dict):
            _copy_summary_keys(derived, graph_derived)

    evidence = response.get("evidence") or {}
    if isinstance(evidence, dict):
        _copy_summary_keys(derived, evidence)
        graph_context = evidence.get("graph_context")
        if isinstance(graph_context, dict):
            _copy_summary_keys(derived, graph_context)
    return derived


def extract_retrieval_evidence(response: dict[str, Any]) -> Any:
    initial_evidence = _initial_retrieved_evidence(response.get("retrieved_evidence"))
    if initial_evidence:
        return initial_evidence
    return response.get("retrieved_evidence")


def extract_reasoning_steps(response: dict[str, Any]) -> Any:
    raw = response.get("reasoning_steps")
    if not isinstance(raw, dict):
        return raw
    return {
        "subqueries": {
            "text": raw.get("text_queries") or [],
            "kg": raw.get("kg_queries") or [],
            "text_expanded": raw.get("text_expanded_queries") or [],
            "kg_expanded": raw.get("kg_expanded_queries") or [],
        },
        "reasoning": {
            "text_final": raw.get("text_final_reasoning"),
            "kg_final": raw.get("kg_final_reasoning"),
            "final": raw.get("final_reasoning"),
        },
        "verification": {
            "text": raw.get("text_verification"),
            "kg": raw.get("kg_verification"),
        },
    }


def _initial_retrieved_evidence(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return _initial_retrieved_evidence(value.get("graph_retrieval"))

    if isinstance(value, list):
        return [
            item
            for item in value
            if isinstance(item, dict) and item.get("stage") == INITIAL_STAGE
        ]
    return []


def _initial_contexts_from_retrieved_evidence(value: Any) -> list[str]:
    contexts = []
    for item in _initial_retrieved_evidence(value):
        text = _first_text(item, "context", "text", "content")
        if text:
            contexts.append(text)
    return contexts


def _copy_summary_keys(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key in DERIVED_CONTEXT_KEYS:
        value = source.get(key)
        if value:
            target.setdefault(key, value)


def _contexts_from_retrieved_evidence(value: Any) -> list[str]:
    contexts: list[str] = []
    if isinstance(value, dict):
        markdown_chunks = value.get("markdown_chunks")
        if isinstance(markdown_chunks, list):
            for chunk in markdown_chunks:
                text = _first_text(chunk, "text", "content")
                if text:
                    contexts.append(text)
        contexts.extend(_contexts_from_retrieved_evidence(value.get("graph_retrieval")))
        return contexts

    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                text = _first_text(item, "context", "text", "content")
                if text:
                    contexts.append(text)
            elif isinstance(item, str) and item.strip():
                contexts.append(item.strip())
    return contexts


def _dropped_context_count(metadata: dict[str, Any]) -> int:
    total = 0
    for key, value in metadata.items():
        if key.startswith("dropped_") and key.endswith("_count") and isinstance(value, int):
            total += value
    return total


def run_sample(
    pipeline: UnifiedRetrievalPipeline,
    sample: EvaluationSample,
    mode: str,
    top_k: int,
) -> dict[str, Any]:
    try:
        response = pipeline.query(
            question=sample.question,
            mode=mode,
            top_k=top_k,
            include_evidence=True,
        )
        contexts = extract_contexts(response)
        retrieved_contexts = extract_retrieved_contexts(response)
        response_metadata = response.get("metadata") or {}
        result = EvaluationResult(
            id=sample.id,
            question=sample.question,
            reference=sample.reference,
            mode=response.get("mode") or mode,
            answer=response.get("answer") or "",
            contexts=contexts,
            retrieved_contexts=retrieved_contexts,
            retrieval_evidence=extract_retrieval_evidence(response),
            derived_contexts=extract_derived_contexts(response),
            reasoning_steps=extract_reasoning_steps(response),
            citations=list(response.get("citations") or []),
            latency_ms=response.get("total_time_ms"),
            retrieval_time_ms=response.get("retrieval_time_ms"),
            synthesis_time_ms=response.get("synthesis_time_ms"),
            token_usage=response.get("token_usage") or response_metadata.get("token_usage"),
            effective_top_k_markdown=response_metadata.get("effective_top_k_markdown"),
            effective_top_k_graph=response_metadata.get("effective_top_k_graph"),
            retrieved_markdown_count=response_metadata.get("retrieved_markdown_count"),
            retrieved_graph_count=response_metadata.get("retrieved_graph_count"),
            dropped_context_count=_dropped_context_count(response_metadata),
            invalid_citations=list(response_metadata.get("invalid_citations") or []),
            tags=sample.tags,
            top_k=top_k,
            context_count=len(retrieved_contexts),
            status="ok",
            error=None,
            metadata={**sample.metadata, "response_metadata": response_metadata},
        )
        return asdict(result)
    except Exception as exc:
        result = EvaluationResult(
            id=sample.id,
            question=sample.question,
            reference=sample.reference,
            mode=mode,
            answer="",
            contexts=[],
            retrieved_contexts=[],
            retrieval_evidence=[],
            derived_contexts={},
            reasoning_steps=None,
            citations=[],
            latency_ms=None,
            retrieval_time_ms=None,
            synthesis_time_ms=None,
            token_usage=None,
            effective_top_k_markdown=None,
            effective_top_k_graph=None,
            retrieved_markdown_count=None,
            retrieved_graph_count=None,
            dropped_context_count=0,
            invalid_citations=[],
            tags=sample.tags,
            top_k=top_k,
            context_count=0,
            status="error",
            error=str(exc),
            metadata=sample.metadata,
        )
        return asdict(result)


def _iter_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _iter_strings(item)


def result_contains_error(row: dict[str, Any], error_contains: str = "429") -> bool:
    markers = [*PROVIDER_ERROR_MARKERS]
    if error_contains:
        markers.append(error_contains)
    return any(marker in text for text in _iter_strings(row) for marker in markers)


def is_unanswered_or_failed(row: dict[str, Any] | None, error_contains: str = "429") -> bool:
    if not row:
        return True
    answer = row.get("answer")
    return (
        not isinstance(answer, str)
        or not answer.strip()
        or row.get("status") == "error"
        or bool(row.get("error"))
        or result_contains_error(row, error_contains=error_contains)
    )


def _normalize_key_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _row_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row.get("id") or ""), str(row.get("mode") or "")


def _question_key(question: Any, mode: str) -> tuple[str, str]:
    return _normalize_key_text(question), mode


def retry_failed_results(
    dataset_path: str | Path,
    results_path: str | Path,
    output_path: str | Path,
    modes: Sequence[str] | None = None,
    top_k: int = 5,
    error_contains: str = "429",
    verbose: bool = False,
) -> list[dict[str, Any]]:
    dataset_rows = load_dataset(dataset_path)
    samples = [parse_sample(row) for row in dataset_rows]
    dataset_has_ids = any(row.get("id") for row in dataset_rows)
    existing_rows = load_dataset(results_path)
    existing_by_key = {_row_key(row): row for row in existing_rows}
    existing_by_question = {
        _question_key(row.get("question"), str(row.get("mode") or "")): row
        for row in existing_rows
        if row.get("question") and row.get("mode")
    }
    selected_modes = list(modes or sorted({str(row.get("mode")) for row in existing_rows if row.get("mode")}))
    if not selected_modes:
        selected_modes = ALL_MODES

    pipeline = UnifiedRetrievalPipeline(RAGConfig())
    merged = []
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    kept_count = 0
    retried_count = 0
    missing_count = 0
    total = len(samples) * len(selected_modes)
    current = 0

    with output.open("w", encoding="utf-8") as f:
        for sample_index, sample in enumerate(samples, start=1):
            for mode in selected_modes:
                current += 1
                key = (sample.id, mode)
                existing = existing_by_key.get(key) if dataset_has_ids else None
                if existing is None:
                    existing = existing_by_question.get(_question_key(sample.question, mode))
                should_retry = is_unanswered_or_failed(existing, error_contains=error_contains)
                if not should_retry:
                    kept_count += 1
                    result = existing
                    action = "keep"
                else:
                    if existing is None:
                        missing_count += 1
                    retried_count += 1
                    action = "retry"
                    result = run_sample(pipeline, sample, mode=mode, top_k=top_k)

                merged.append(result)
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
                f.flush()

                if verbose:
                    print(
                        f"[{current}/{total}] {action} sample={sample_index}/{len(samples)} "
                        f"mode={mode} id={sample.id} status={result.get('status')} error={result.get('error') or ''}",
                        flush=True,
                    )

    write_csv(output.with_suffix(".csv"), merged)
    if verbose:
        print(f"Retry summary: kept={kept_count} retried={retried_count} missing={missing_count}", flush=True)
    return merged


def run_dataset(
    dataset_path: str | Path,
    output_path: str | Path,
    mode: str = "semantic_search",
    top_k: int = 5,
    verbose: bool = False,
) -> list[dict[str, Any]]:
    results = run_dataset_for_modes(dataset_path, output_path, modes=[mode], top_k=top_k, verbose=verbose)
    return results


def run_dataset_for_modes(
    dataset_path: str | Path,
    output_path: str | Path,
    modes: Sequence[str] | None = None,
    top_k: int = 5,
    verbose: bool = False,
) -> list[dict[str, Any]]:
    samples = [parse_sample(row) for row in load_dataset(dataset_path)]
    pipeline = UnifiedRetrievalPipeline(RAGConfig())
    selected_modes = list(modes or ALL_MODES)
    results = []

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    total = len(samples) * len(selected_modes)
    current = 0
    with output.open("w", encoding="utf-8") as f:
        for sample_index, sample in enumerate(samples, start=1):
            for mode in selected_modes:
                current += 1
                if verbose:
                    print(
                        f"[{current}/{total}] sample={sample_index}/{len(samples)} "
                        f"mode={mode} id={sample.id} question={sample.question[:120]}",
                        flush=True,
                    )
                result = run_sample(pipeline, sample, mode=mode, top_k=top_k)
                results.append(result)
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
                f.flush()
                if verbose:
                    latency = result.get("latency_ms")
                    latency_text = f" latency_ms={latency:.1f}" if isinstance(latency, (int, float)) else ""
                    print(
                        f"    -> status={result.get('status')} contexts={result.get('context_count')}"
                        f"{latency_text} error={result.get('error') or ''}",
                        flush=True,
                    )

    csv_path = output.with_suffix(".csv")
    write_csv(csv_path, results)
    return results


def _first_text(item: Any, *keys: str) -> str | None:
    if isinstance(item, str):
        return item.strip() or None
    if not isinstance(item, dict):
        return None
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None
