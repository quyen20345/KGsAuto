"""Token-aware Markdown chunking strategies."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from services.rag_system.retrieval.token_counter import TokenCounter
from services.rag_system.schemas import Chunk


HEADER_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
SENTENCE_RE = re.compile(r"(?<=[.!?。！？])\s+|(?<=\.)\s+(?=[A-ZÀ-Ỵ0-9])", re.UNICODE)


class MarkdownChunker:
    """Markdown-aware chunker optimized for embedding retrieval.

    The default strategy preserves Markdown sections, merges short paragraphs,
    splits long text on sentence boundaries, and only hard-splits by tokens as a
    fallback. Chunk size is controlled by the embedding model token budget.
    """

    def __init__(self, config):
        self.config = config
        self.max_tokens = getattr(config, "chunk_max_tokens", 100)
        self.overlap_tokens = getattr(config, "chunk_overlap_tokens", 20)
        self.min_tokens = getattr(config, "chunk_min_tokens", 15)
        self.max_chunk_size = getattr(config, "max_chunk_size", 512)
        self.chunk_overlap = getattr(config, "chunk_overlap", 50)

        if self.chunk_overlap >= self.max_chunk_size:
            raise ValueError("chunk_overlap must be smaller than max_chunk_size")
        if self.overlap_tokens >= self.max_tokens:
            raise ValueError("chunk_overlap_tokens must be smaller than chunk_max_tokens")
        if self.min_tokens >= self.max_tokens:
            raise ValueError("chunk_min_tokens must be smaller than chunk_max_tokens")

        self.token_counter = TokenCounter(getattr(config, "embedding_model", "paraphrase-multilingual-mpnet-base-v2"))

    def chunk_file(self, md_path: Path) -> list[Chunk]:
        content = md_path.read_text(encoding="utf-8", errors="ignore")
        doc_id = md_path.stem
        metadata, main_content = self._parse_markdown(content)
        title = metadata.get("title", doc_id)
        main_content = self._promote_headers(main_content)

        strategy = getattr(self.config, "chunk_strategy", "section")
        if strategy == "fixed":
            return self._chunk_token_windows(main_content, doc_id, title, "Content", md_path, metadata, 0, 0)
        if strategy == "sentence":
            return self._chunk_blocks_by_tokens(
                self._split_sentences(main_content), doc_id, title, "Content", md_path, metadata, 0, 0
            )
        if strategy != "section":
            raise ValueError(f"Unsupported chunk_strategy: {strategy}. Use section, fixed, or sentence.")
        return self._hierarchical_chunking(main_content, doc_id, title, md_path, metadata)

    def _promote_headers(self, text: str) -> str:
        """Promote numbered lines (1. Topic) to markdown headers."""

        return re.sub(r"(?m)^(\d+\.\s+[^\n]+)$", r"### \1", text)

    def _parse_markdown(self, content: str) -> tuple[dict[str, Any], str]:
        metadata: dict[str, Any] = {}
        main_content = content

        metadata_match = re.search(r"## Metadata\s*\n(.*?)\n##", content, re.DOTALL)
        if metadata_match:
            metadata_text = metadata_match.group(1)
            for line in metadata_text.split("\n"):
                match = re.match(r"-\s*\*\*(.+?)\*\*:\s*(.+)", line)
                if match:
                    key = match.group(1).lower().replace(" ", "_")
                    metadata[key] = match.group(2).strip()

            content_match = re.search(r"## Content\s*\n(.*)", content, re.DOTALL)
            if content_match:
                main_content = content_match.group(1)

        return metadata, main_content

    def _hierarchical_chunking(
        self,
        content: str,
        doc_id: str,
        title: str,
        source_path: Path,
        metadata: dict[str, Any],
    ) -> list[Chunk]:
        chunks: list[Chunk] = []
        chunk_index = 0
        sections = self._split_sections(content)
        for section_title, section_text, char_offset in sections:
            new_chunks = self._recursive_split(
                section_text,
                doc_id=doc_id,
                title=title,
                section=section_title,
                source_path=source_path,
                metadata=metadata,
                char_offset=char_offset,
                start_index=chunk_index,
            )
            chunks.extend(new_chunks)
            chunk_index += len(new_chunks)
        return chunks

    def _split_sections(self, content: str) -> list[tuple[str, str, int]]:
        matches = list(HEADER_RE.finditer(content))
        if not matches:
            return [("General", content, 0)] if content.strip() else []

        sections: list[tuple[str, str, int]] = []
        prefix = content[: matches[0].start()]
        if prefix.strip():
            sections.append(("General", prefix, 0))

        for index, match in enumerate(matches):
            title = match.group(2).strip()
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
            text = content[start:end]
            if text.strip():
                sections.append((title, text, start))
        return sections

    def _recursive_split(
        self,
        text: str,
        doc_id: str,
        title: str,
        section: str,
        source_path: Path,
        metadata: dict[str, Any],
        char_offset: int,
        start_index: int,
    ) -> list[Chunk]:
        if self.token_counter.count(text) <= self.max_tokens:
            return self._maybe_create_single_chunk(text, doc_id, title, section, source_path, metadata, char_offset, start_index)

        paragraphs = self._split_paragraphs(text)
        return self._chunk_blocks_by_tokens(paragraphs, doc_id, title, section, source_path, metadata, char_offset, start_index)

    def _split_paragraphs(self, text: str) -> list[str]:
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
        return paragraphs or [text.strip()]

    def _split_sentences(self, text: str) -> list[str]:
        sentences = [part.strip() for part in SENTENCE_RE.split(text) if part.strip()]
        return sentences or [text.strip()]

    def _chunk_blocks_by_tokens(
        self,
        blocks: list[str],
        doc_id: str,
        title: str,
        section: str,
        source_path: Path,
        metadata: dict[str, Any],
        char_offset: int,
        start_index: int,
    ) -> list[Chunk]:
        chunks: list[Chunk] = []
        current_blocks: list[str] = []
        current_tokens = 0
        current_offset = char_offset
        next_offset = char_offset

        def flush() -> None:
            nonlocal current_blocks, current_tokens, current_offset
            if not current_blocks:
                return
            merged = "\n\n".join(current_blocks).strip()
            if merged:
                chunks.append(
                    self._create_chunk(
                        merged, doc_id, title, section, source_path, metadata, current_offset, start_index + len(chunks)
                    )
                )
            current_blocks = []
            current_tokens = 0

        for block in blocks:
            block = block.strip()
            if not block:
                continue
            block_tokens = self.token_counter.count(block)

            if block_tokens > self.max_tokens:
                flush()
                sentences = self._split_sentences(block)
                if len(sentences) > 1:
                    sentence_chunks = self._chunk_blocks_by_tokens(
                        sentences, doc_id, title, section, source_path, metadata, next_offset, start_index + len(chunks)
                    )
                    chunks.extend(sentence_chunks)
                else:
                    chunks.extend(
                        self._chunk_token_windows(
                            block, doc_id, title, section, source_path, metadata, next_offset, start_index + len(chunks)
                        )
                    )
                next_offset += len(block) + 2
                current_offset = next_offset
                continue

            if current_blocks and current_tokens + block_tokens > self.max_tokens:
                flush()
                current_offset = next_offset

            if not current_blocks:
                current_offset = next_offset
            current_blocks.append(block)
            current_tokens += block_tokens
            next_offset += len(block) + 2

        flush()
        return chunks

    def _chunk_token_windows(
        self,
        text: str,
        doc_id: str,
        title: str,
        section: str,
        source_path: Path,
        metadata: dict[str, Any],
        char_offset: int,
        start_index: int,
    ) -> list[Chunk]:
        windows = self.token_counter.split_by_tokens(text, self.max_tokens, self.overlap_tokens)
        chunks: list[Chunk] = []
        cursor = char_offset
        for window in windows:
            if self.token_counter.count(window) < self.min_tokens and chunks:
                previous = chunks[-1]
                previous.text = f"{previous.text}\n\n{window}".strip()
                previous.char_end = cursor + len(window)
                continue
            chunks.append(self._create_chunk(window, doc_id, title, section, source_path, metadata, cursor, start_index + len(chunks)))
            cursor += len(window)
        return chunks

    def _maybe_create_single_chunk(
        self,
        text: str,
        doc_id: str,
        title: str,
        section: str,
        source_path: Path,
        metadata: dict[str, Any],
        char_start: int,
        chunk_index: int,
    ) -> list[Chunk]:
        if not text.strip():
            return []
        return [self._create_chunk(text, doc_id, title, section, source_path, metadata, char_start, chunk_index)]

    def _create_chunk(
        self,
        text: str,
        doc_id: str,
        title: str,
        section: str,
        source_path: Path,
        metadata: dict[str, Any],
        char_start: int,
        chunk_index: int,
    ) -> Chunk:
        raw_text = text.strip()
        enriched_text = raw_text
        if getattr(self.config, "context_enrichment", True):
            enriched_text = f"{title} > {section}: {raw_text}"

        return Chunk(
            chunk_id=f"{doc_id}_{chunk_index}",
            doc_id=doc_id,
            source_path=str(source_path),
            title=title,
            section=section,
            text=enriched_text,
            metadata=metadata,
            char_start=char_start,
            char_end=char_start + len(raw_text),
            chunk_index=chunk_index,
        )

    def _chunk_by_fixed_size(
        self,
        content: str,
        doc_id: str,
        title: str,
        source_path: Path,
        metadata: dict[str, Any],
    ) -> list[Chunk]:
        """Backward-compatible wrapper for older tests/callers."""

        return self._chunk_token_windows(content, doc_id, title, "Content", source_path, metadata, 0, 0)
