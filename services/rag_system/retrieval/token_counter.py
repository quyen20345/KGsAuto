"""Token counting helpers for RAG chunking.

The chunker prefers the embedding model tokenizer so chunks stay within the
model context window. If the tokenizer is unavailable locally, it falls back to
a lightweight regex tokenizer to keep indexing usable offline.
"""

from __future__ import annotations

import re
from functools import lru_cache


TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)


@lru_cache(maxsize=4)
def _load_tokenizer(model_name: str):
    try:
        from transformers import AutoTokenizer

        return AutoTokenizer.from_pretrained(model_name, local_files_only=True)
    except Exception:
        return None


class TokenCounter:
    """Count/split tokens using the embedding model tokenizer when available."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.tokenizer = _load_tokenizer(model_name)

    def count(self, text: str) -> int:
        if not text:
            return 0
        if self.tokenizer is not None:
            return len(self.tokenizer.encode(text, add_special_tokens=False))
        return len(TOKEN_RE.findall(text))

    def split_by_tokens(self, text: str, max_tokens: int, overlap_tokens: int = 0) -> list[str]:
        """Split text into token windows.

        This is used only as a last-resort hard split after paragraph and
        sentence boundaries have failed to produce small enough chunks.
        """

        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if overlap_tokens >= max_tokens:
            raise ValueError("overlap_tokens must be smaller than max_tokens")
        if self.count(text) <= max_tokens:
            return [text.strip()] if text.strip() else []

        if self.tokenizer is not None:
            token_ids = self.tokenizer.encode(text, add_special_tokens=False)
            step = max_tokens - overlap_tokens
            chunks = []
            for start in range(0, len(token_ids), step):
                window = token_ids[start : start + max_tokens]
                if not window:
                    continue
                chunks.append(self.tokenizer.decode(window, skip_special_tokens=True).strip())
            return [chunk for chunk in chunks if chunk]

        tokens = TOKEN_RE.findall(text)
        step = max_tokens - overlap_tokens
        chunks = []
        for start in range(0, len(tokens), step):
            window = tokens[start : start + max_tokens]
            if window:
                chunks.append(" ".join(window).strip())
        return [chunk for chunk in chunks if chunk]
