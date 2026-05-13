"""Tests for markdown indexing payload and embedding inputs."""

from pathlib import Path

from services.rag_system.config import RAGConfig
from services.rag_system.retrieval.indexing import Indexer
from services.rag_system.retrieval.store import Store


class FakeStore:
    payloads = None

    def __init__(self, config):
        self.config = config

    def collection_exists(self):
        return True

    def create_collection(self):
        raise AssertionError("collection should already exist")

    def upsert_chunks(self, chunks, show_progress=True):
        FakeStore.payloads = chunks
        return len(chunks)


def test_indexer_payload_excludes_title_and_source_fields(tmp_path, monkeypatch):
    markdown_dir = tmp_path / "docs"
    markdown_dir.mkdir()
    (markdown_dir / "001_Test title.md").write_text("# Test title\n\nBody content.", encoding="utf-8")

    monkeypatch.setattr("services.rag_system.retrieval.indexing.Store", FakeStore)
    FakeStore.payloads = None

    config = RAGConfig(markdown_dir=markdown_dir)
    stats = Indexer(config).index_all()

    assert stats["chunks_created"] == 1
    assert FakeStore.payloads == [
        {
            "chunk_id": "001_Test title_0",
            "text": "Test title: Body content.",
            "chunk_index": 0,
        }
    ]


class FakeVector:
    def __init__(self, values):
        self.values = values

    def tolist(self):
        return self.values


class FakeEmbedder:
    def __init__(self):
        self.texts = None

    def encode(self, texts, batch_size=None, show_progress_bar=None):
        self.texts = texts
        return [FakeVector([1.0, 0.0]) for _ in texts]


class FakeClient:
    def __init__(self):
        self.upserted = []

    def upsert(self, collection_name, points):
        self.upserted.extend(points)


def test_store_embeds_text_field_only():
    store = Store.__new__(Store)
    store.config = type("Config", (), {"embedding_batch_size": 8})()
    store.collection_name = "test_collection"
    store.embedder = FakeEmbedder()
    store.client = FakeClient()

    chunks = [
        {
            "chunk_id": "chunk_0",
            "text": "Body content only.",
            "title": "This title must not be embedded",
            "chunk_index": 0,
        }
    ]

    indexed = store.upsert_chunks(chunks, show_progress=False)

    assert indexed == 1
    assert store.embedder.texts == ["Body content only."]
    assert store.client.upserted[0].payload == chunks[0]
