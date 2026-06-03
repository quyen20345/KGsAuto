from services.config import (
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    NEO4J_PASSWORD,
    NEO4J_URI,
    NEO4J_USER,
)
import os

VECTOR_INDEX_NAME = os.getenv("VECTOR_INDEX_NAME", "entity_embeddings")
