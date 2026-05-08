import pytest
from fastapi.testclient import TestClient

from apps.chat_api import main, service


class FakePipeline:
    async def aquery(self, question, mode, top_k, include_evidence):
        return {
            "question": question,
            "mode": mode,
            "answer": "ok",
            "citations": ["c1"],
            "evidence": {"markdown_chunks": []} if include_evidence else None,
            "retrieval_time_ms": 1.0,
            "synthesis_time_ms": 2.0,
            "total_time_ms": 3.0,
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
    assert set(body["modes"]) == {"semantic_search", "graph_search", "naive_grag", "hybrid"}


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
    assert body["error"] is None


def test_query_rejects_invalid_mode(client):
    res = client.post("/query", json={"message": "Hiệu trưởng là ai?", "mode": "invalid"})
    assert res.status_code == 400
    assert "Unsupported unified retrieval mode" in res.json()["detail"]


def test_query_rejects_empty_message(client):
    res = client.post("/query", json={"message": ""})
    assert res.status_code == 422
