# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient

from apps.chat_api import main, service


class FakePipeline:
    async def aquery(self, question, mode, top_k=None, include_evidence=True):
        return {
            "question": question,
            "mode": mode,
            "answer": "ok",
            "citations": ["c1"],
            "evidence": {"markdown_chunks": []} if include_evidence else None,
            "retrieval_time_ms": 1.0,
            "synthesis_time_ms": 2.0,
            "total_time_ms": 3.0,
            "reasoning_steps": ["find relevant context", "synthesize answer"],
            "metadata": {"top_k": top_k},
        }


@pytest.fixture
def client():
    return TestClient(main.app)


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["service"] == "chat_api"
    assert set(body["modes"]) == {"semantic_search", "graph_search", "naive_grag", "hybrid", "direct"}


def test_modes(client):
    res = client.get("/modes")
    assert res.status_code == 200
    body = res.json()
    assert body["default_mode"] == "semantic_search"
    assert "hybrid" in body["modes"]


def test_query_success(monkeypatch, client):
    monkeypatch.setattr(service, "get_pipeline", lambda: FakePipeline())

    res = client.post(
        "/query",
        json={
            "message": "Hiệu trưởng là ai?",
            "mode": "semantic_search",
            "top_k": 5,
            "include_evidence": True,
            "conversation_id": "conv-1",
        },
    )

    assert res.status_code == 200
    body = res.json()
    assert body["answer"] == "ok"
    assert body["mode"] == "semantic_search"
    assert body["conversation_id"] == "conv-1"
    assert body["citations"] == ["c1"]
    assert body["evidence"] == {"markdown_chunks": []}
    assert body["metadata"]["total_time_ms"] == 3.0
    assert body["metadata"]["reasoning_steps"] == ["find relevant context", "synthesize answer"]
    assert body["error"] is None


def test_query_rejects_invalid_mode(client):
    res = client.post("/query", json={"message": "Hiệu trưởng là ai?", "mode": "invalid"})
    assert res.status_code == 400
    assert "Unsupported unified retrieval mode" in res.json()["detail"]


def test_query_rejects_empty_message(client):
    res = client.post("/query", json={"message": ""})
    assert res.status_code == 422


def test_openai_models(client):
    res = client.get("/v1/models")
    assert res.status_code == 200
    body = res.json()
    assert body["object"] == "list"
    assert {model["id"] for model in body["data"]} == {"semantic_search", "graph_search", "naive_grag", "hybrid", "direct"}


def test_openai_chat_completion_success(monkeypatch, client):
    monkeypatch.setattr(service, "get_pipeline", lambda: FakePipeline())

    res = client.post(
        "/v1/chat/completions",
        json={
            "model": "semantic_search",
            "messages": [{"role": "user", "content": "Hiệu trưởng là ai?"}],
            "stream": False,
            "include_evidence": True,
        },
    )

    assert res.status_code == 200
    body = res.json()
    assert body["object"] == "chat.completion"
    assert body["choices"][0]["message"]["content"] == "ok"
    assert body["kgsauto"]["mode"] == "semantic_search"
    assert body["kgsauto"]["evidence"] == {"markdown_chunks": []}
    assert body["kgsauto"]["metadata"]["reasoning_steps"] == ["find relevant context", "synthesize answer"]


def test_openai_chat_completion_stream(monkeypatch, client):
    monkeypatch.setattr(service, "get_pipeline", lambda: FakePipeline())

    with client.stream(
        "POST",
        "/v1/chat/completions",
        json={
            "model": "semantic_search",
            "messages": [{"role": "user", "content": "Hiệu trưởng là ai?"}],
            "stream": True,
        },
    ) as res:
        assert res.status_code == 200
        text = "".join(res.iter_text())

    assert "chat.completion.chunk" in text
    assert "status" in text
    assert "Đang truy xuất tài liệu" in text
    assert "reasoning_step" in text
    assert "find relevant context" in text
    assert "ok" in text
    assert "data: [DONE]" in text


def test_ask_endpoint_success(monkeypatch, client):
    monkeypatch.setattr(main, "get_pipeline", lambda: FakePipeline())

    res = client.post(
        "/ask",
        json={
            "message": "Hello!",
            "conversation_id": "test-conv",
        },
    )

    assert res.status_code == 200
    body = res.json()
    assert body["answer"] == "ok"
    assert body["conversation_id"] == "test-conv"
