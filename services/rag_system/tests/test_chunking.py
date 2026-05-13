"""Tests for semantic Markdown chunking."""

import pytest

from services.rag_system.config import RAGConfig
from services.rag_system.retrieval.chunking import MarkdownChunker


class MockPath:
    def __init__(self, text: str, stem: str = "doc"):
        self._text = text
        self.stem = stem

    def read_text(self, encoding="utf-8", errors="ignore"):
        return self._text

    def __str__(self):
        return f"/test/{self.stem}.md"


class TestMarkdownChunker:
    def test_clean_markdown_file_uses_markdown_sections(self):
        config = RAGConfig(chunk_strategy="section", chunk_max_tokens=40, chunk_overlap_tokens=10, context_enrichment=False)
        chunker = MarkdownChunker(config)
        md_content = """# Chuyên ngành Quản lý hệ thống thông tin

Chương trình đào tạo thạc sĩ ngành Quản lý hệ thống thông tin có mục tiêu đào tạo cụ thể:

1. Mục tiêu chung

- Bổ sung và nâng cao các kiến thức về Hệ thống thông tin.
- Đào tạo các chuyên gia có hiểu biết toàn diện về Hệ thống Thông tin.

## Mục khác

Nội dung khác vẫn được giữ trong văn bản nguồn trước khi chia cửa sổ token.

Thông tin bổ sung về chương trình, định hướng nghiên cứu, kỹ năng thực hành, kỹ năng phân tích thiết kế hệ thống thông tin và khả năng tiếp tục học tập nghiên cứu sau tốt nghiệp.
"""

        chunks = chunker.chunk_file(MockPath(md_content, "386_Chuyên ngành Quản lý hệ thống thông tin"))

        assert len(chunks) > 1
        assert chunks[0].chunk_id == "386_Chuyên ngành Quản lý hệ thống thông tin_0"
        assert chunks[0].title == "Chuyên ngành Quản lý hệ thống thông tin"
        assert chunks[0].section == "Chuyên ngành Quản lý hệ thống thông tin"
        assert chunks[0].chunk_index == 0
        assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
        assert chunks[0].text.startswith("Chương trình đào tạo thạc sĩ")
        assert "# Chuyên ngành" not in chunks[0].text
        assert all(chunk.text.strip() for chunk in chunks)

    def test_fixed_strategy_uses_token_windows(self):
        content = "# Title\n\n" + "This is a test document. " * 50
        chunker = MarkdownChunker(
            RAGConfig(chunk_strategy="fixed", chunk_max_tokens=20, chunk_overlap_tokens=5, context_enrichment=False)
        )

        chunks = chunker.chunk_file(MockPath(content, "test_doc"))

        assert len(chunks) > 1
        assert chunks[0].section == "Title"
        assert chunks[0].text.startswith("This is a test document")

    def test_title_falls_back_to_filename_without_h1(self):
        chunks = MarkdownChunker(RAGConfig(context_enrichment=False)).chunk_file(
            MockPath("Không có heading, chỉ có nội dung.", "fallback_doc")
        )

        assert len(chunks) == 1
        assert chunks[0].title == "fallback_doc"
        assert chunks[0].section == "fallback_doc"
        assert chunks[0].text == "Không có heading, chỉ có nội dung."

    def test_only_title_returns_no_chunks(self):
        chunks = MarkdownChunker(RAGConfig()).chunk_file(MockPath("# Only Title\n\n", "only_title"))

        assert chunks == []

    def test_chunk_overlap_validation(self):
        with pytest.raises(ValueError, match="chunk_overlap must be smaller than max_chunk_size"):
            RAGConfig(chunk_strategy="fixed", max_chunk_size=100, chunk_overlap=100)

    def test_header_hierarchy_is_preserved_in_section(self):
        content = """# Tuyển sinh

## Phương thức xét tuyển

### Xét học bạ

Nội dung xét học bạ.
"""
        chunks = MarkdownChunker(RAGConfig(chunk_strategy="section", context_enrichment=False)).chunk_file(MockPath(content))

        assert len(chunks) == 1
        assert chunks[0].title == "Tuyển sinh"
        assert chunks[0].section == "Phương thức xét tuyển > Xét học bạ"

    def test_context_enrichment_uses_title_and_section_path(self):
        content = """# Tuyển sinh

## Phương thức xét tuyển

### Xét học bạ

Nội dung xét học bạ.
"""
        chunks = MarkdownChunker(RAGConfig(chunk_strategy="section", context_enrichment=True)).chunk_file(MockPath(content))

        assert chunks[0].text.startswith("Tuyển sinh > Phương thức xét tuyển > Xét học bạ: Nội dung xét học bạ.")

    def test_vietnamese_sentence_splitting_keeps_common_abbreviations(self):
        chunker = MarkdownChunker(
            RAGConfig(chunk_strategy="sentence", chunk_max_tokens=12, chunk_overlap_tokens=2, chunk_min_tokens=4, context_enrichment=False)
        )
        content = "# Tư vấn\n\nTS. Nguyễn Văn A phụ trách tư vấn. Thí sinh liên hệ phòng tuyển sinh."

        chunks = chunker.chunk_file(MockPath(content))
        joined = "\n".join(chunk.text for chunk in chunks)

        assert "TS. Nguyễn Văn A" in joined
        assert all(chunk.text != "TS." for chunk in chunks)

    def test_markdown_table_is_preserved_when_under_budget(self):
        content = """# Chỉ tiêu

## Bảng ngành

| Ngành | Chỉ tiêu |
| --- | --- |
| Công nghệ thông tin | 300 |
| Trí tuệ nhân tạo | 100 |
"""
        chunks = MarkdownChunker(
            RAGConfig(chunk_strategy="section", chunk_max_tokens=80, chunk_overlap_tokens=10, context_enrichment=False)
        ).chunk_file(MockPath(content))

        assert len(chunks) == 1
        assert "| Ngành | Chỉ tiêu |" in chunks[0].text
        assert "| Trí tuệ nhân tạo | 100 |" in chunks[0].text

    def test_markdown_list_is_preserved_when_under_budget(self):
        content = """# Hồ sơ

## Giấy tờ

- Bản sao học bạ
- Căn cước công dân
- Phiếu đăng ký xét tuyển
"""
        chunks = MarkdownChunker(
            RAGConfig(chunk_strategy="section", chunk_max_tokens=80, chunk_overlap_tokens=10, context_enrichment=False)
        ).chunk_file(MockPath(content))

        assert len(chunks) == 1
        assert "- Bản sao học bạ" in chunks[0].text
        assert "- Phiếu đăng ký xét tuyển" in chunks[0].text

    def test_long_paragraph_falls_back_to_smaller_chunks(self):
        sentence = "Thí sinh cần đáp ứng điều kiện xét tuyển và nộp hồ sơ đúng hạn. "
        content = "# Tuyển sinh\n\n## Điều kiện\n\n" + sentence * 30
        chunker = MarkdownChunker(
            RAGConfig(chunk_strategy="section", chunk_max_tokens=35, chunk_overlap_tokens=5, context_enrichment=False)
        )

        chunks = chunker.chunk_file(MockPath(content))

        assert len(chunks) > 1
        assert all(chunk.text.strip() for chunk in chunks)
        assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))

    def test_tiny_trailing_chunk_merges_with_previous_chunk(self):
        content = "# Tuyển sinh\n\n## Điều kiện\n\n" + ("Nội dung tuyển sinh quan trọng. " * 8) + "Ghi chú."
        chunker = MarkdownChunker(
            RAGConfig(chunk_strategy="section", chunk_max_tokens=35, chunk_overlap_tokens=5, chunk_min_tokens=10, context_enrichment=False)
        )

        chunks = chunker.chunk_file(MockPath(content))

        assert "Ghi chú." in chunks[-1].text
        assert chunker.token_counter.count(chunks[-1].text) >= 10 or len(chunks) == 1
