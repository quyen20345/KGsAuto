"""Markdown chunking strategies"""

import re
from pathlib import Path
from typing import List, Dict, Any

from services.rag_system.schemas import Chunk


class MarkdownChunker:
    """Enhanced chunker with hierarchical splitting and context enrichment."""

    def __init__(self, config):
        self.config = config
        self.max_chunk_size = config.max_chunk_size
        self.chunk_overlap = config.chunk_overlap

    def chunk_file(self, md_path: Path) -> List[Chunk]:
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        doc_id = md_path.stem
        metadata, main_content = self._parse_markdown(content)
        title = metadata.get('title', doc_id)

        # 1. Pre-process: Promote semantic headers (e.g., "1. Topic") to markdown headers
        main_content = self._promote_headers(main_content)

        if self.config.chunk_strategy == "fixed":
            return self._chunk_by_fixed_size(main_content, doc_id, title, md_path, metadata)

        # Use recursive hierarchical splitting
        return self._hierarchical_chunking(main_content, doc_id, title, md_path, metadata)

    def _promote_headers(self, text: str) -> str:
        """Promote numbered items (1., 2.) at the start of a line to headers."""
        return re.sub(r'\n(\d+\.\s+[A-Z].+)\n', r'\n### \1\n', text)

    def _parse_markdown(self, content: str) -> tuple[Dict[str, Any], str]:
        metadata = {}
        main_content = content

        metadata_match = re.search(r'## Metadata\s*\n(.*?)\n##', content, re.DOTALL)
        if metadata_match:
            metadata_text = metadata_match.group(1)
            for line in metadata_text.split('\n'):
                match = re.match(r'-\s*\*\*(.+?)\*\*:\s*(.+)', line)
                if match:
                    key = match.group(1).lower().replace(' ', '_')
                    value = match.group(2).strip()
                    metadata[key] = value

            content_match = re.search(r'## Content\s*\n(.*)', content, re.DOTALL)
            if content_match:
                main_content = content_match.group(1)

        return metadata, main_content

    def _hierarchical_chunking(
        self,
        content: str,
        doc_id: str,
        title: str,
        source_path: Path,
        metadata: Dict[str, Any],
    ) -> List[Chunk]:
        chunks = []
        chunk_index = 0

        # Split by markdown headers of any level (#, ##, ###)
        parts = re.split(r'\n(#+\s+.+)\n', content)
        
        current_section = "General"
        current_text = ""
        offset = 0

        for i, part in enumerate(parts):
            if i % 2 == 1: # Header
                if current_text.strip():
                    new_chunks = self._recursive_split(
                        current_text, doc_id, title, current_section, source_path, metadata, offset, chunk_index
                    )
                    chunks.extend(new_chunks)
                    chunk_index += len(new_chunks)
                
                current_section = part.strip().lstrip('#').strip()
                current_text = ""
                offset += len(parts[i-1]) + len(part) + 2
            else:
                current_text = part

        if current_text.strip():
            new_chunks = self._recursive_split(
                current_text, doc_id, title, current_section, source_path, metadata, offset, chunk_index
            )
            chunks.extend(new_chunks)

        return chunks

    def _recursive_split(
        self,
        text: str,
        doc_id: str,
        title: str,
        section: str,
        source_path: Path,
        metadata: Dict[str, Any],
        char_offset: int,
        start_index: int,
    ) -> List[Chunk]:
        """Split text recursively: Paragraph -> Fixed."""
        if len(text) <= self.max_chunk_size:
            return [self._create_chunk(text, doc_id, title, section, source_path, metadata, char_offset, start_index)]

        paragraphs = text.split('\n\n')
        if len(paragraphs) > 1:
            chunks = []
            p_offset = char_offset
            for p in paragraphs:
                if not p.strip():
                    p_offset += len(p) + 2
                    continue
                sub_chunks = self._recursive_split(p, doc_id, title, section, source_path, metadata, p_offset, start_index + len(chunks))
                chunks.extend(sub_chunks)
                p_offset += len(p) + 2
            return chunks

        chunks = []
        step = self.max_chunk_size - self.chunk_overlap
        for i in range(0, len(text), step):
            sub_text = text[i:i + self.max_chunk_size]
            if sub_text.strip():
                chunks.append(
                    self._create_chunk(sub_text, doc_id, title, section, source_path, metadata, char_offset + i, start_index + len(chunks))
                )
        return chunks

    def _create_chunk(
        self,
        text: str,
        doc_id: str,
        title: str,
        section: str,
        source_path: Path,
        metadata: Dict[str, Any],
        char_start: int,
        chunk_index: int
    ) -> Chunk:
        enriched_text = text.strip()
        if getattr(self.config, 'context_enrichment', True):
            prefix = f"{title} > {section}: "
            enriched_text = prefix + enriched_text

        return Chunk(
            chunk_id=f"{doc_id}_{chunk_index}",
            doc_id=doc_id,
            source_path=str(source_path),
            title=title,
            section=section,
            text=enriched_text,
            metadata=metadata,
            char_start=char_start,
            char_end=char_start + len(text),
            chunk_index=chunk_index,
        )

    def _chunk_by_fixed_size(self, content: str, doc_id: str, title: str, source_path: Path, metadata: Dict[str, Any]) -> List[Chunk]:
        return self._recursive_split(content, doc_id, title, "Content", source_path, metadata, 0, 0)
