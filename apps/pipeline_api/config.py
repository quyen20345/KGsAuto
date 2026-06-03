import os
from pathlib import Path

from services.config import settings as service_settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "uet"
EXTRACTED_DIR = PROJECT_ROOT / "data" / "extracted"
ER_ARTIFACTS_DIR = PROJECT_ROOT / "data" / "entity_resolution" / "artifacts"
DB_PATH = PROJECT_ROOT / "data" / "pipeline_state.db"

NEO4J_URI = os.getenv("NEO4J_URI", service_settings.neo4j.uri)
NEO4J_USER = os.getenv("NEO4J_USER", service_settings.neo4j.user)
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", service_settings.neo4j.password)

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", service_settings.embedding.model)
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", str(service_settings.embedding.dim)))
VECTOR_INDEX_NAME = os.getenv("VECTOR_INDEX_NAME", "entity_embeddings")
