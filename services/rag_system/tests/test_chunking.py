"""Tests for markdown chunking strategies."""

import pytest
from pathlib import Path
from services.rag_system.config import RAGConfig
from services.rag_system.retrieval.chunking import MarkdownChunker


class TestMarkdownChunker:
    def test_fixed_size_chunking(self):
        config = RAGConfig(chunk_strategy="fixed", chunk_max_tokens=20, chunk_overlap_tokens=5)
        chunker = MarkdownChunker(config)
        
        # Create a temp file
        content = "This is a test document. " * 20
        
        class MockPath:
            stem = "test_doc"
            def read_text(self, encoding="utf-8", errors="ignore"):
                return f"## Metadata\n- **title**: Test\n## Content\n{content}"
            def __str__(self):
                return "/test/doc.md"
        
        chunks = chunker.chunk_file(MockPath())
        assert len(chunks) > 0
        assert all(chunker.token_counter.count(c.text) <= 30 for c in chunks)  # Including prefix
        
    def test_hierarchical_chunking_by_headers(self):
        config = RAGConfig(chunk_strategy="section", chunk_max_tokens=80, chunk_overlap_tokens=10)
        chunker = MarkdownChunker(config)
        
        md_content = """## Metadata
- **title**: Test Doc
## Content
# Header 1
Content under header 1.
More content here.

# Header 2
Content under header 2.
Even more content.
"""
        
        class MockPath:
            stem = "test_doc"
            def read_text(self, encoding="utf-8", errors="ignore"):
                return md_content
            def __str__(self):
                return "/test/doc.md"
        
        chunks = chunker.chunk_file(MockPath())
        assert len(chunks) >= 2
        
        # Check sections are captured
        sections = [c.section for c in chunks]
        assert "Header 1" in sections or "Header 2" in sections
        
    def test_promote_headers(self):
        config = RAGConfig(chunk_strategy="section", chunk_max_tokens=80, chunk_overlap_tokens=10)
        chunker = MarkdownChunker(config)
        
        # Text with numbered items that should become headers
        text = "1. Introduction\nSome intro text.\n2. Methodology\nSome method text."
        result = chunker._promote_headers(text)
        
        assert "### 1. Introduction" in result
        assert "### 2. Methodology" in result

    def test_chunk_overlap_validation(self):
        with pytest.raises(ValueError, match="chunk_overlap must be smaller than max_chunk_size"):
            RAGConfig(chunk_strategy="fixed", max_chunk_size=100, chunk_overlap=100)

    def test_context_enrichment(self):
        config = RAGConfig(
            chunk_strategy="fixed", 
            chunk_max_tokens=30,
            chunk_overlap_tokens=5,
            context_enrichment=True
        )
        chunker = MarkdownChunker(config)
        
        chunks = chunker._recursive_split(
            "Test content here.",
            doc_id="doc",
            title="My Title",
            section="My Section",
            source_path=Path("/test.md"),
            metadata={},
            char_offset=0,
            start_index=0
        )
        
        assert len(chunks) == 1
        assert "My Title" in chunks[0].text
        assert "My Section" in chunks[0].text
