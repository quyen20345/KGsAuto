"""Token-aware Markdown chunking strategies."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from services.rag_system.retrieval.token_counter import TokenCounter
from services.rag_system.schemas import Chunk


HEADER_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
LIST_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")
VIETNAMESE_ABBREVIATIONS = {
    "TS.",
    "ThS.",
    "PGS.",
    "GS.",
    "TP.",
    "QĐ.",
    "ĐH.",
    "VD.",
    "STT.",
    "v.v.",
}


class MarkdownChunker:
    """Markdown chunker using semantic structure before token windows."""

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
        title = self._extract_title(content) or doc_id
        metadata = {}
        body = self._strip_title_heading(content).strip()
        if not body:
            return []

        strategy = getattr(self.config, "chunk_strategy", "section")
        if strategy == "fixed":
            return self._chunk_token_windows(body, doc_id, title, title, md_path, metadata, 0, 0)
        if strategy == "sentence":
            blocks = self._split_sentences(body)
            return self._chunk_blocks_by_tokens(blocks, doc_id, title, title, md_path, metadata, 0, 0)
        return self._hierarchical_chunking(body, doc_id, title, md_path, metadata)

    def _promote_headers(self, text: str) -> str:
        """Return text unchanged."""

        return text

    def _extract_title(self, text: str) -> str | None:
        """Extract the first H1 as document title from clean Markdown."""

        match = re.search(r"^#\s+(.+?)\s*$", text, re.MULTILINE)
        return match.group(1).strip() if match else None

    def _strip_title_heading(self, text: str) -> str:
        """Remove the first H1 because payload stores body text only."""

        return re.sub(r"^#\s+.+?\s*\n+", "", text, count=1, flags=re.MULTILINE)

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
        sections = self._split_sections(content, title)
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

    def _split_sections(self, content: str, default_section: str = "General") -> list[tuple[str, str, int]]:
        matches = list(HEADER_RE.finditer(content))
        if not matches:
            return [(default_section, content, 0)] if content.strip() else []

        sections: list[tuple[str, str, int]] = []
        header_stack: list[tuple[int, str]] = []
        prefix = content[: matches[0].start()]
        if prefix.strip():
            sections.append((default_section, prefix, 0))

        for index, match in enumerate(matches):
            level = len(match.group(1))
            heading = match.group(2).strip()
            header_stack = [(item_level, item_title) for item_level, item_title in header_stack if item_level < level]
            header_stack.append((level, heading))

            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
            text = content[start:end]
            if text.strip():
                sections.append((" > ".join(item_title for _, item_title in header_stack), text, start))
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

        blocks = self._split_markdown_blocks(text)
        return self._chunk_blocks_by_tokens(blocks, doc_id, title, section, source_path, metadata, char_offset, start_index)

    def _split_markdown_blocks(self, text: str) -> list[str]:
        lines = text.strip().splitlines()
        blocks: list[str] = []
        current: list[str] = []
        current_kind: str | None = None
        in_fence = False

        def line_kind(line: str) -> str:
            stripped = line.strip()
            if not stripped:
                return "blank"
            if stripped.startswith("```"):
                return "fence"
            if "|" in stripped and stripped.count("|") >= 2:
                return "table"
            if LIST_RE.match(stripped):
                return "list"
            return "paragraph"

        def flush() -> None:
            nonlocal current, current_kind
            merged = "\n".join(current).strip()
            if merged:
                blocks.append(merged)
            current = []
            current_kind = None

        for line in lines:
            kind = line_kind(line)
            if in_fence:
                current.append(line)
                if kind == "fence":
                    in_fence = False
                    flush()
                continue
            if kind == "blank":
                flush()
                continue
            if kind == "fence":
                flush()
                current = [line]
                current_kind = "fence"
                in_fence = True
                continue
            if current and current_kind != kind:
                flush()
            current.append(line)
            current_kind = kind
        flush()
        return blocks or [text.strip()]

    def _split_paragraphs(self, text: str) -> list[str]:
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
        return paragraphs or [text.strip()]

    def _split_sentences(self, text: str) -> list[str]:
        text = text.strip()
        if not text:
            return []

        sentences: list[str] = []
        start = 0
        for match in re.finditer(r"[.!?;。！？]", text):
            end = match.end()
            if end >= len(text) or not text[end].isspace():
                continue
            previous_token = text[start:end].strip().split()[-1] if text[start:end].strip().split() else ""
            if previous_token in VIETNAMESE_ABBREVIATIONS:
                continue
            if match.group(0) == "." and self._is_numeric_dot(text, match.start()):
                continue
            next_index = self._next_non_space_index(text, end)
            if next_index is None:
                continue
            next_char = text[next_index]
            if not (next_char.isupper() or next_char.isdigit() or next_char in "-*+"):
                continue
            sentences.append(text[start:end].strip())
            start = next_index

        tail = text[start:].strip()
        if tail:
            sentences.append(tail)
        return sentences or [text]

    def _split_clauses(self, text: str) -> list[str]:
        clauses = [part.strip() for part in re.split(r"(?<=[;:])\s+|\n+", text) if part.strip()]
        return clauses if len(clauses) > 1 else [text.strip()]

    def _is_numeric_dot(self, text: str, dot_index: int) -> bool:
        return dot_index > 0 and dot_index + 1 < len(text) and text[dot_index - 1].isdigit() and text[dot_index + 1].isdigit()

    def _next_non_space_index(self, text: str, start: int) -> int | None:
        for index in range(start, len(text)):
            if not text[index].isspace():
                return index
        return None

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
        cursor = char_offset

        def flush() -> None:
            nonlocal current_blocks, current_tokens, current_offset
            if not current_blocks:
                return
            merged = "\n\n".join(current_blocks).strip()
            if merged:
                self._append_or_merge_chunk(chunks, merged, doc_id, title, section, source_path, metadata, current_offset, start_index)
            current_blocks = []
            current_tokens = 0

        for block in blocks:
            block = block.strip()
            if not block:
                continue
            block_offset = self._find_block_offset(block, source_text="\n\n".join(blocks), fallback=cursor - char_offset) + char_offset
            block_tokens = self.token_counter.count(block)

            if block_tokens > self.max_tokens:
                flush()
                chunks.extend(
                    self._split_oversized_block(block, doc_id, title, section, source_path, metadata, block_offset, start_index + len(chunks))
                )
                cursor = block_offset + len(block) + 2
                current_offset = cursor
                continue

            if current_blocks and current_tokens + block_tokens > self.max_tokens:
                flush()
                current_offset = block_offset

            if not current_blocks:
                current_offset = block_offset
            current_blocks.append(block)
            current_tokens += block_tokens
            cursor = block_offset + len(block) + 2

        flush()
        return chunks

    def _split_oversized_block(
        self,
        block: str,
        doc_id: str,
        title: str,
        section: str,
        source_path: Path,
        metadata: dict[str, Any],
        char_offset: int,
        start_index: int,
    ) -> list[Chunk]:
        sentences = self._split_sentences(block)
        if len(sentences) > 1:
            return self._chunk_blocks_by_tokens(sentences, doc_id, title, section, source_path, metadata, char_offset, start_index)

        clauses = self._split_clauses(block)
        if len(clauses) > 1:
            return self._chunk_blocks_by_tokens(clauses, doc_id, title, section, source_path, metadata, char_offset, start_index)

        return self._chunk_token_windows(block, doc_id, title, section, source_path, metadata, char_offset, start_index)

    def _find_block_offset(self, block: str, source_text: str, fallback: int) -> int:
        found = source_text.find(block, max(fallback, 0))
        return found if found >= 0 else fallback

    def _append_or_merge_chunk(
        self,
        chunks: list[Chunk],
        text: str,
        doc_id: str,
        title: str,
        section: str,
        source_path: Path,
        metadata: dict[str, Any],
        char_start: int,
        start_index: int,
    ) -> None:
        if self.token_counter.count(text) < self.min_tokens and chunks:
            previous = chunks[-1]
            merged_text = f"{previous.text}\n\n{text}".strip()
            if self.token_counter.count(merged_text) <= self.max_tokens + self.overlap_tokens:
                previous.text = merged_text
                previous.char_end = max(previous.char_end, char_start + len(text))
                return
        chunks.append(self._create_chunk(text, doc_id, title, section, source_path, metadata, char_start, start_index + len(chunks)))

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
                cursor += len(window)
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
        chunk_text = self._enrich_text(raw_text, title, section)

        return Chunk(
            chunk_id=f"{doc_id}_{chunk_index}",
            doc_id=doc_id,
            source_path=str(source_path),
            title=title,
            section=section,
            text=chunk_text,
            metadata=metadata,
            char_start=char_start,
            char_end=char_start + len(raw_text),
            chunk_index=chunk_index,
        )

    def _enrich_text(self, text: str, title: str, section: str) -> str:
        if not getattr(self.config, "context_enrichment", False):
            return text
        prefix = self._build_context_prefix(title, section)
        if not prefix or text.startswith(prefix):
            return text
        return f"{prefix}: {text}"

    def _build_context_prefix(self, title: str, section: str) -> str:
        title = " ".join(title.split())
        section = " ".join(section.split())
        if not section or section in {"General", title}:
            return title
        if section.startswith(f"{title} >"):
            return section
        return f"{title} > {section}"

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
