import os

from services.config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER

# Embedding configuration for vector search
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-mpnet-base-v2")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "768"))
