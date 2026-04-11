from __future__ import annotations

import hashlib
import logging
import math

logger = logging.getLogger(__name__)

# Global cache for sentence-transformers models
_MODEL_CACHE: dict[str, any] = {}


def stable_hash_embedding(text: str, dim: int = 128) -> list[float]:
    """
    Lightweight deterministic embedding for tests and CPU-only runs.
    """
    vec = [0.0] * dim
    if not text:
        return vec

    tokens = text.lower().split()
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        idx = int(digest[:8], 16) % dim
        sign = 1.0 if int(digest[8:10], 16) % 2 == 0 else -1.0
        weight = 1.0 + (int(digest[10:12], 16) / 255.0)
        vec[idx] += sign * weight

    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        return vec
    return [x / norm for x in vec]


def get_embedding_model(model_name: str):
    """
    Load and cache sentence-transformers model.

    Args:
        model_name: Model name (e.g., 'paraphrase-multilingual-mpnet-base-v2')

    Returns:
        SentenceTransformer model instance
    """
    if model_name not in _MODEL_CACHE:
        try:
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading embedding model: {model_name}")
            _MODEL_CACHE[model_name] = SentenceTransformer(model_name)
            dim = _MODEL_CACHE[model_name].get_sentence_embedding_dimension()
            logger.info(f"Model loaded successfully, dimension={dim}")
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            raise

    return _MODEL_CACHE[model_name]


def semantic_embedding(text: str, model_name: str = "paraphrase-multilingual-mpnet-base-v2") -> list[float]:
    """
    Create semantic embedding using sentence-transformers.
    Supports multilingual text (Vietnamese + English).

    Args:
        text: Input text to embed
        model_name: Sentence-transformers model name

    Returns:
        Vector embedding as list of floats
    """
    if not text or not text.strip():
        model = get_embedding_model(model_name)
        dim = model.get_sentence_embedding_dimension()
        return [0.0] * dim

    try:
        model = get_embedding_model(model_name)
        vector = model.encode(text, convert_to_numpy=True, show_progress_bar=False)
        return vector.tolist()
    except Exception as e:
        logger.error(f"Semantic embedding failed for text (len={len(text)}): {e}")
        logger.warning("Falling back to hash embedding")
        # Fallback to hash embedding with appropriate dimension
        model = get_embedding_model(model_name)
        dim = model.get_sentence_embedding_dimension()
        return stable_hash_embedding(text, dim=dim)


def create_embedding(
    text: str,
    method: str = "semantic",
    model_name: str | None = None,
    dim: int = 128,
) -> list[float]:
    """
    Unified embedding interface supporting multiple methods.

    Args:
        text: Input text to embed
        method: "semantic" or "hash"
        model_name: Model name for semantic embedding (default: paraphrase-multilingual-mpnet-base-v2)
        dim: Dimension for hash embedding

    Returns:
        Vector embedding as list of floats
    """
    if method == "semantic":
        model_name = model_name or "paraphrase-multilingual-mpnet-base-v2"
        return semantic_embedding(text, model_name)
    else:
        return stable_hash_embedding(text, dim)
