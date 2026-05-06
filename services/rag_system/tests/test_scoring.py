"""Tests for Ragas scoring helpers."""

import json

from services.rag_system.evaluation import scoring


def test_score_results_loads_dotenv(tmp_path, monkeypatch):
    results_path = tmp_path / "results.jsonl"
    output_path = tmp_path / "scored.jsonl"
    results_path.write_text(
        json.dumps(
            {
                "question": "Q?",
                "answer": "A",
                "contexts": ["C"],
                "reference": "R",
                "status": "ok",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text(
        "OPENAI_API_KEY=test-key\nOPENAI_BASE_URL=http://example.test/v1\nOPENAI_MODEL=test-model\n",
        encoding="utf-8",
    )
    for name in (
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "OPENAI_MODEL",
        "OPENAI_COMPATIBLE_API_KEY",
        "OPENAI_COMPATIBLE_BASE_URL",
        "OPENAI_COMPATIBLE_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)

    def fake_score_with_ragas(rows, metric_names):
        assert scoring._resolve_ragas_openai_config() == {
            "api_key": "test-key",
            "base_url": "http://example.test/v1",
            "model": "test-model",
        }
        return [{"faithfulness": 1.0}]

    monkeypatch.setattr(scoring, "_score_with_ragas", fake_score_with_ragas)

    rows = scoring.score_results(results_path, output_path, metrics=["faithfulness"])

    assert rows[0]["ragas_score_status"] == "scored"
    assert rows[0]["faithfulness"] == 1.0


def test_score_with_ragas_uses_v2_dataset_schema(monkeypatch):
    captured = {}

    class FakeDataset:
        @classmethod
        def from_list(cls, rows):
            captured["dataset_rows"] = rows
            return rows

    class FakeResult:
        def to_pandas(self):
            class FakeFrame:
                def iterrows(self):
                    return iter([(0, {"faithfulness": 0.5})])

            return FakeFrame()

    def fake_evaluate(dataset, metrics, llm):
        captured["dataset"] = dataset
        captured["metrics"] = metrics
        captured["llm"] = llm
        return FakeResult()

    monkeypatch.setitem(__import__("sys").modules, "datasets", type("DatasetsModule", (), {"Dataset": FakeDataset}))
    monkeypatch.setattr(scoring, "_build_ragas_llm", lambda: "llm")
    monkeypatch.setitem(
        __import__("sys").modules,
        "ragas",
        type("RagasModule", (), {"evaluate": fake_evaluate}),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "ragas.metrics",
        type(
            "MetricsModule",
            (),
            {
                "answer_relevancy": "answer_relevancy",
                "context_precision": "context_precision",
                "context_recall": "context_recall",
                "faithfulness": "faithfulness",
            },
        ),
    )

    scores = scoring._score_with_ragas(
        [
            {
                "question": "What?",
                "answer": "This.",
                "contexts": ["Context"],
                "reference": "Reference",
            }
        ],
        ["faithfulness"],
    )

    assert captured["dataset_rows"] == [
        {
            "user_input": "What?",
            "response": "This.",
            "retrieved_contexts": ["Context"],
            "reference": "Reference",
        }
    ]
    assert captured["metrics"] == ["faithfulness"]
    assert captured["llm"] == "llm"
    assert scores == [{"faithfulness": 0.5, "answer_relevancy": None, "context_precision": None, "context_recall": None}]
