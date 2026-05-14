import json

import pytest

from services.rag_system.evaluation import runner
from services.rag_system.evaluation.runner import (
    EvaluationSample,
    extract_contexts,
    extract_derived_contexts,
    extract_reasoning_steps,
    extract_retrieval_evidence,
    extract_retrieved_contexts,
    run_sample,
)


def test_graph_retrieved_contexts_are_initial_only():
    initial = {"stage": "initial", "context": "INITIAL"}
    response = {
        "retrieved_evidence": [
            initial,
            {"stage": "text_subquery", "context": "TEXT SUBQUERY"},
            {"stage": "relational_expansion", "context": "EXPANSION"},
        ]
    }

    assert extract_retrieved_contexts(response) == ["INITIAL"]
    assert extract_contexts(response) == ["INITIAL"]
    assert extract_retrieval_evidence(response) == [initial]


def test_hybrid_retrieved_contexts_use_graph_initial_only():
    response = {
        "retrieved_evidence": {
            "markdown_chunks": [{"text": "SEMANTIC"}],
            "graph_retrieval": [
                {"stage": "initial", "context": "GRAPH INITIAL"},
                {"stage": "kg_subquery", "context": "KG SUBQUERY"},
            ],
        }
    }

    assert extract_retrieved_contexts(response) == ["GRAPH INITIAL"]


def test_semantic_retrieved_contexts_fallback_still_works():
    response = {"retrieved_evidence": {"markdown_chunks": [{"text": "SEMANTIC"}]}}

    assert extract_retrieved_contexts(response) == ["SEMANTIC"]


def test_derived_contexts_only_include_text_and_kg_summaries():
    response = {
        "derived_evidence": {
            "text_summary": "TEXT SUMMARY",
            "kg_summary": "KG SUMMARY",
            "extra": "DO NOT INCLUDE",
        },
        "evidence": {"graph_reasoning": {"some": "reasoning"}},
    }

    assert extract_derived_contexts(response) == {
        "text_summary": "TEXT SUMMARY",
        "kg_summary": "KG SUMMARY",
    }


def test_hybrid_derived_contexts_flatten_graph_derived():
    response = {
        "derived_evidence": {
            "graph_derived": {
                "text_summary": "TEXT SUMMARY",
                "kg_summary": "KG SUMMARY",
            }
        }
    }

    assert extract_derived_contexts(response) == {
        "text_summary": "TEXT SUMMARY",
        "kg_summary": "KG SUMMARY",
    }


def test_reasoning_steps_are_normalized_to_subqueries_reasoning_and_verification():
    response = {
        "reasoning_steps": {
            "text_queries": [["q1", "summary", "answer"]],
            "kg_queries": [["kg1", "kg summary", "kg answer"]],
            "text_expanded_queries": ["q2"],
            "kg_expanded_queries": ["kg2"],
            "text_final_reasoning": "text final",
            "kg_final_reasoning": "kg final",
            "final_reasoning": "final",
            "text_verification": "verified text",
            "kg_verification": "verified kg",
        }
    }

    assert extract_reasoning_steps(response) == {
        "subqueries": {
            "text": [["q1", "summary", "answer"]],
            "kg": [["kg1", "kg summary", "kg answer"]],
            "text_expanded": ["q2"],
            "kg_expanded": ["kg2"],
        },
        "reasoning": {
            "text_final": "text final",
            "kg_final": "kg final",
            "final": "final",
        },
        "verification": {"text": "verified text", "kg": "verified kg"},
    }


def test_run_sample_separates_retrieved_derived_and_reasoning_fields():
    class FakePipeline:
        def query(self, question, mode, top_k, include_evidence):
            assert question == "question"
            assert mode == "graph_search"
            assert top_k == 5
            assert include_evidence is True
            return {
                "mode": "graph_search",
                "answer": "answer",
                "retrieved_evidence": [
                    {"stage": "initial", "context": "INITIAL"},
                    {"stage": "text_subquery", "context": "SUBQUERY"},
                ],
                "derived_evidence": {
                    "text_summary": "TEXT",
                    "kg_summary": "KG",
                    "extra": "ignored",
                },
                "reasoning_steps": {
                    "text_queries": [["q1", "summary", ""]],
                    "kg_queries": [["kg1", "kg summary", "kg answer"]],
                    "text_expanded_queries": ["q1 expanded"],
                    "kg_expanded_queries": ["kg1 expanded"],
                    "text_final_reasoning": "text reasoning",
                    "kg_final_reasoning": "kg reasoning",
                    "final_reasoning": "final reasoning",
                    "text_verification": "yes",
                    "kg_verification": "yes",
                },
                "citations": [],
                "total_time_ms": 12.3,
            }

    result = run_sample(
        FakePipeline(),
        EvaluationSample(id="sample-1", question="question", reference="reference"),
        mode="graph_search",
        top_k=5,
    )

    assert result["contexts"] == ["INITIAL"]
    assert result["retrieved_contexts"] == ["INITIAL"]
    assert result["retrieval_evidence"] == [{"stage": "initial", "context": "INITIAL"}]
    assert result["derived_contexts"] == {"text_summary": "TEXT", "kg_summary": "KG"}
    assert result["reasoning_steps"] == {
        "subqueries": {
            "text": [["q1", "summary", ""]],
            "kg": [["kg1", "kg summary", "kg answer"]],
            "text_expanded": ["q1 expanded"],
            "kg_expanded": ["kg1 expanded"],
        },
        "reasoning": {
            "text_final": "text reasoning",
            "kg_final": "kg reasoning",
            "final": "final reasoning",
        },
        "verification": {"text": "yes", "kg": "yes"},
    }
    assert result["context_count"] == 1


def test_is_unanswered_or_failed_detects_nested_provider_errors():
    assert not runner.is_unanswered_or_failed({"status": "ok", "answer": "Câu trả lời hợp lệ", "error": None})
    assert runner.is_unanswered_or_failed({"status": "error", "answer": "", "error": "boom"})
    assert runner.is_unanswered_or_failed({"status": "ok", "answer": "", "error": None})
    assert runner.is_unanswered_or_failed(
        {
            "status": "ok",
            "answer": "OpenAICompatible Error (host=http://localhost:20128/v1): Error code: 429",
            "error": None,
        }
    )
    assert runner.is_unanswered_or_failed(
        {
            "status": "ok",
            "answer": "Có answer nhưng graph bị lỗi",
            "error": None,
            "reasoning_steps": {
                "verification": {
                    "text": "rate_limit_exceeded",
                }
            },
        }
    )


def test_retry_failed_results_matches_csv_without_ids_by_question(tmp_path, monkeypatch):
    dataset_path = tmp_path / "dataset.csv"
    results_path = tmp_path / "results.jsonl"
    output_path = tmp_path / "retried.jsonl"
    dataset_path.write_text("question,reference\nq1,r1\nq2,r2\n", encoding="utf-8")
    results_path.write_text(
        "\n".join(
            [
                json.dumps({"id": "generated-1", "question": "q1", "mode": "hybrid", "answer": "ok", "status": "ok", "error": None}),
                json.dumps({"id": "generated-2", "question": "q2", "mode": "hybrid", "answer": "OpenAICompatible Error 429", "status": "ok", "error": None}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(runner, "UnifiedRetrievalPipeline", lambda config: object())

    def fake_run_sample(pipeline, sample, mode, top_k):
        return {
            "id": sample.id,
            "question": sample.question,
            "reference": sample.reference,
            "mode": mode,
            "answer": "retried",
            "contexts": [],
            "retrieved_contexts": [],
            "retrieval_evidence": [],
            "derived_contexts": {},
            "reasoning_steps": None,
            "citations": [],
            "latency_ms": None,
            "tags": [],
            "top_k": top_k,
            "context_count": 0,
            "status": "ok",
            "error": None,
            "metadata": {},
        }

    monkeypatch.setattr(runner, "run_sample", fake_run_sample)

    rows = runner.retry_failed_results(dataset_path, results_path, output_path, modes=["hybrid"])

    assert rows[0]["id"] == "generated-1"
    assert rows[0]["answer"] == "ok"
    assert rows[1]["question"] == "q2"
    assert rows[1]["answer"] == "retried"


def test_run_dataset_for_modes_writes_completed_rows_incrementally(tmp_path, monkeypatch):
    dataset_path = tmp_path / "dataset.jsonl"
    output_path = tmp_path / "results.jsonl"
    dataset_path.write_text(
        '\n'.join(
            [
                json.dumps({"id": "one", "question": "q1"}),
                json.dumps({"id": "two", "question": "q2"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(runner, "UnifiedRetrievalPipeline", lambda config: object())

    def fake_run_sample(pipeline, sample, mode, top_k):
        if sample.id == "two":
            raise RuntimeError("boom")
        return {
            "id": sample.id,
            "question": sample.question,
            "reference": sample.reference,
            "mode": mode,
            "answer": "answer",
            "contexts": [],
            "retrieved_contexts": [],
            "retrieval_evidence": [],
            "derived_contexts": {},
            "reasoning_steps": None,
            "citations": [],
            "latency_ms": None,
            "tags": [],
            "top_k": top_k,
            "context_count": 0,
            "status": "ok",
            "error": None,
            "metadata": {},
        }

    monkeypatch.setattr(runner, "run_sample", fake_run_sample)

    with pytest.raises(RuntimeError, match="boom"):
        runner.run_dataset_for_modes(dataset_path, output_path, modes=["graph_search"])

    rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert [row["id"] for row in rows] == ["one"]
