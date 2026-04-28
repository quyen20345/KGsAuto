"""Minimal RAG evaluation runner."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

from services.rag_system.config import RAGConfig
from services.rag_system.core.unified_pipeline import UnifiedRetrievalPipeline


@dataclass
class EvaluationSample:
    id: str
    question: str
    reference: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class EvaluationResult:
    id: str
    question: str
    reference: str
    mode: str
    answer: str
    contexts: list[str]
    citations: list[str]
    latency_ms: float | None
    tags: list[str]


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: str | Path, rows: Iterable[dict[str, Any]]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: str | Path, rows: Iterable[dict[str, Any]]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["id", "question", "reference", "mode", "answer", "contexts", "citations", "latency_ms", "tags"]
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            csv_row = {key: row.get(key) for key in fieldnames}
            csv_row["contexts"] = json.dumps(csv_row.get("contexts") or [], ensure_ascii=False)
            csv_row["citations"] = json.dumps(csv_row.get("citations") or [], ensure_ascii=False)
            csv_row["tags"] = json.dumps(csv_row.get("tags") or [], ensure_ascii=False)
            writer.writerow(csv_row)


def parse_sample(row: dict[str, Any]) -> EvaluationSample:
    return EvaluationSample(
        id=str(row["id"]),
        question=str(row["question"]),
        reference=str(row.get("reference") or ""),
        tags=list(row.get("tags") or []),
    )


def extract_contexts(response: dict[str, Any]) -> list[str]:
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
        text = _first_text(graph_context, "fact_text", "description", "text", "content")
        if text:
            contexts.append(text)

    return contexts


def run_dataset(
    dataset_path: str | Path,
    output_path: str | Path,
    mode: str = "semantic_search",
    top_k: int = 5,
) -> list[dict[str, Any]]:
    samples = [parse_sample(row) for row in load_jsonl(dataset_path)]
    pipeline = UnifiedRetrievalPipeline(RAGConfig())
    results = []

    for sample in samples:
        response = pipeline.query(
            question=sample.question,
            mode=mode,
            top_k=top_k,
            include_evidence=True,
        )
        result = EvaluationResult(
            id=sample.id,
            question=sample.question,
            reference=sample.reference,
            mode=response.get("mode") or mode,
            answer=response.get("answer") or "",
            contexts=extract_contexts(response),
            citations=list(response.get("citations") or []),
            latency_ms=response.get("total_time_ms"),
            tags=sample.tags,
        )
        results.append(asdict(result))

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
