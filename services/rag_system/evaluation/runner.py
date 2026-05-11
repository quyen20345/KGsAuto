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
    "tags",
    "top_k",
    "context_count",
    "status",
    "error",
    "metadata",
]


ALL_MODES = ["semantic_search", "graph_search", "naive_grag", "hybrid"]


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
        derived.update(response_derived)

    evidence = response.get("evidence") or {}
    graph_context = evidence.get("graph_context")
    if isinstance(graph_context, dict):
        for key in ("text_summary", "kg_summary"):
            value = graph_context.get(key)
            if value:
                derived.setdefault(key, value)
    if evidence.get("graph_reasoning"):
        derived.setdefault("graph_reasoning", evidence["graph_reasoning"])
    return derived


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
        result = EvaluationResult(
            id=sample.id,
            question=sample.question,
            reference=sample.reference,
            mode=response.get("mode") or mode,
            answer=response.get("answer") or "",
            contexts=contexts,
            retrieved_contexts=retrieved_contexts,
            retrieval_evidence=response.get("retrieved_evidence"),
            derived_contexts=extract_derived_contexts(response),
            reasoning_steps=response.get("reasoning_steps"),
            citations=list(response.get("citations") or []),
            latency_ms=response.get("total_time_ms"),
            tags=sample.tags,
            top_k=top_k,
            context_count=len(retrieved_contexts),
            status="ok",
            error=None,
            metadata=sample.metadata,
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
            tags=sample.tags,
            top_k=top_k,
            context_count=0,
            status="error",
            error=str(exc),
            metadata=sample.metadata,
        )
        return asdict(result)


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

    total = len(samples) * len(selected_modes)
    current = 0
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
            if verbose:
                latency = result.get("latency_ms")
                latency_text = f" latency_ms={latency:.1f}" if isinstance(latency, (int, float)) else ""
                print(
                    f"    -> status={result.get('status')} contexts={result.get('context_count')}"
                    f"{latency_text} error={result.get('error') or ''}",
                    flush=True,
                )

    write_jsonl(output_path, results)
    csv_path = Path(output_path).with_suffix(".csv")
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
