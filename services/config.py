"""Shared infrastructure configuration for KGsAuto services."""

from __future__ import annotations

import os

from dotenv import load_dotenv


load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "OpenAICompatible")
LLM_MODEL = os.getenv("LLM_MODEL", "cx/gpt-5.3-codex")

OPENAI_COMPATIBLE_API_KEY = os.getenv("OPENAI_COMPATIBLE_API_KEY")
OPENAI_COMPATIBLE_BASE_URL = os.getenv("OPENAI_COMPATIBLE_BASE_URL")
OPENAI_COMPATIBLE_MODEL = os.getenv("OPENAI_COMPATIBLE_MODEL")
