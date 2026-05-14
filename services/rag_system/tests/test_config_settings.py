from __future__ import annotations

import importlib
import sys

import pytest


CONFIG_ENV_NAMES = [
    "KGSAUTO_LOAD_DOTENV",
    "CONFIG_STRICT",
    "NEO4J_URI",
    "NEO4J_USER",
    "NEO4J_PASSWORD",
    "QDRANT_URL",
    "LLM_PROVIDER",
    "LLM_MODEL",
    "OPENAI_COMPATIBLE_API_KEY",
    "OPENAI_COMPATIBLE_BASE_URL",
    "OPENAI_COMPATIBLE_MODEL",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_MODEL",
    "CX_API_KEY",
    "GOOGLE_API_KEY",
    "DEFAULT_MODEL",
    "EMBEDDING_MODEL",
    "EMBEDDING_DIM",
    "EMBEDDING_DEVICE",
    "GRAPH_KEYWORD_MAX_TERMS",
    "GRAPH_ENABLE_SUBSTRING_FALLBACK",
    "RAGAS_EMBEDDING_API_KEY",
    "RAGAS_EMBEDDING_MODEL",
    "RAGAS_EMBEDDING_BASE_URL",
    "RAGAS_EMBEDDING_DELAY_SECONDS",
    "NVIDIA_API_KEY",
    "NVIDIA_EMBED_MODEL",
    "NVIDIA_BASE_URL",
]


def reload_config(monkeypatch, **env):
    for name in CONFIG_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("KGSAUTO_LOAD_DOTENV", "false")
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    sys.modules.pop("services.config", None)
    return importlib.import_module("services.config")


def test_defaults_load_without_required_secrets(monkeypatch):
    config = reload_config(monkeypatch)

    assert config.settings.neo4j.uri == "bolt://localhost:7687"
    assert config.settings.qdrant.url == "http://localhost:6333"
    assert config.settings.llm.provider == "OpenAICompatible"
    assert config.settings.graph.keyword_max_terms == 16


def test_openai_compatible_key_prefers_canonical(monkeypatch):
    config = reload_config(
        monkeypatch,
        OPENAI_COMPATIBLE_API_KEY="canonical",
        OPENAI_API_KEY="legacy",
    )

    assert config.settings.llm.openai_compatible_api_key == "canonical"
    assert config.OPENAI_COMPATIBLE_API_KEY == "canonical"


def test_openai_compatible_key_falls_back_to_legacy_alias(monkeypatch):
    with pytest.warns(DeprecationWarning):
        config = reload_config(monkeypatch, OPENAI_API_KEY="legacy")

    assert config.settings.llm.openai_compatible_api_key == "legacy"


def test_bool_and_int_parsing(monkeypatch):
    config = reload_config(
        monkeypatch,
        GRAPH_KEYWORD_MAX_TERMS="7",
        GRAPH_ENABLE_SUBSTRING_FALLBACK="false",
    )

    assert config.settings.graph.keyword_max_terms == 7
    assert config.settings.graph.enable_substring_fallback is False


def test_openai_compatible_validation_requires_api_key(monkeypatch):
    config = reload_config(monkeypatch, LLM_PROVIDER="OpenAICompatible")

    with pytest.raises(config.ConfigValidationError, match="OPENAI_COMPATIBLE_API_KEY"):
        config.validate_settings("extraction")


def test_provider_validation_requires_gemini_key(monkeypatch):
    config = reload_config(monkeypatch, LLM_PROVIDER="gemini")

    with pytest.raises(config.ConfigValidationError, match="GOOGLE_API_KEY"):
        config.validate_settings("extraction")


def test_evaluation_embedding_alias(monkeypatch):
    with pytest.warns(DeprecationWarning):
        config = reload_config(monkeypatch, NVIDIA_API_KEY="nvidia")

    assert config.settings.evaluation.ragas_embedding_api_key == "nvidia"
