"""Tests for Ragas test document preparation."""

import csv
import json

from services.rag_system.evaluation.prepare_test_docs import build_candidate, build_candidates, parse_markdown_document, prepare_documents


def test_parse_markdown_document_removes_metadata():
    raw = """# Phong Dao Tao

## Metadata

- **URL**: https://example.test/phong-dao-tao
- **Slug**: phong-dao-tao

## Content

1. Chuc nang: tham muu, giup viec Hieu truong ve dao tao.
"""

    parsed = parse_markdown_document(raw, fallback_title="fallback")

    assert parsed.title == "Phong Dao Tao"
    assert parsed.metadata["url"] == "https://example.test/phong-dao-tao"
    assert "**URL**" not in parsed.content
    assert "Slug" not in parsed.content
    assert parsed.content.startswith("1. Chuc nang")


def test_build_candidate_classifies_ontology_group(tmp_path):
    source = tmp_path / "khoa.md"
    source.write_text(
        """# Khoa Cong nghe Thong tin

## Content

Khoa Cong nghe Thong tin la don vi dao tao truc thuoc Truong Dai hoc Cong nghe.
Khoa co ban chu nhiem, cac bo mon, phong thi nghiem va chuong trinh dao tao.
Nhiem vu cua Khoa la dao tao, nghien cuu va hop tac voi doanh nghiep.
""",
        encoding="utf-8",
    )

    candidate = build_candidate(source, min_content_chars=80)

    assert candidate.reject_reason is None
    assert candidate.primary_group != "unknown"
    assert "FACULTY" in candidate.matched_labels
    assert candidate.score > 0


def test_build_candidate_rejects_metadata_leftover(tmp_path):
    source = tmp_path / "bad.md"
    source.write_text(
        """# Bad Doc

## Content

Noi dung nay bi loi vi van con metadata.

## Metadata

- **URL**: https://example.test/bad
""",
        encoding="utf-8",
    )

    candidate = build_candidate(source, min_content_chars=10)

    assert candidate.reject_reason == "metadata_leftover"


def test_build_candidates_splits_long_document(tmp_path):
    source = tmp_path / "long.md"
    paragraph = (
        "Khoa Cong nghe Thong tin dao tao chuong trinh ky su, quan ly bo mon, "
        "phong thi nghiem, giang vien, sinh vien va hop tac voi doanh nghiep. "
        "Nhiem vu cua Khoa la dao tao, nghien cuu, to chuc hoc phan va cung cap thong tin lien he."
    )
    source.write_text(
        "# Khoa Cong nghe Thong tin\n\n## Content\n\n" + "\n\n".join([paragraph] * 12),
        encoding="utf-8",
    )

    candidates = build_candidates(source, min_content_chars=100, max_content_chars=700)

    assert len(candidates) > 1
    assert all(candidate.char_count <= 700 for candidate in candidates)
    assert all(candidate.source_part_count == len(candidates) for candidate in candidates)
    assert any("Phần" in candidate.title for candidate in candidates)


def test_prepare_documents_writes_clean_docs_manifest_and_summary(tmp_path):
    input_dir = tmp_path / "raw"
    output_dir = tmp_path / "clean"
    manifest_path = tmp_path / "manifest.csv"
    summary_path = tmp_path / "summary.json"
    input_dir.mkdir()

    (input_dir / "001_org.md").write_text(
        """# Phong Cong tac Sinh vien

## Metadata

- **URL**: https://example.test/ctsv
- **Slug**: ctsv

## Content

Phong Cong tac Sinh vien tham muu, giup viec Hieu truong quan ly nguoi hoc.
Phong to chuc cong tac sinh vien, quan ly ho so, hoc bong, viec lam va lien he doanh nghiep.
Phong co to chuc nhan su, truong phong, pho truong phong, email va dia chi lien he.
""",
        encoding="utf-8",
    )
    (input_dir / "002_program.md").write_text(
        """# Chuong trinh dao tao Ky thuat may tinh

## Content

Chuong trinh dao tao ky su nganh Ky thuat may tinh cung cap kien thuc ve he thong nhung.
Sinh vien hoc cac hoc phan co so, hoc phan chuyen nganh va thuc hien do an tot nghiep.
Khoa phu trach dao tao, cap nhat chuan dau ra va to chuc lop hoc cho nguoi hoc.
""",
        encoding="utf-8",
    )
    (input_dir / "003_short.md").write_text(
        """# Short

## Content

Qua ngan.
""",
        encoding="utf-8",
    )

    summary = prepare_documents(
        input_dir=input_dir,
        output_dir=output_dir,
        manifest_path=manifest_path,
        summary_path=summary_path,
        target_count=2,
        min_content_chars=80,
        max_content_chars=1000,
    )

    clean_files = sorted(output_dir.glob("*.md"))
    assert summary["accepted_files"] == 2
    assert summary["input_files"] == 3
    assert summary["candidate_docs"] == 3
    assert summary["max_content_chars"] == 1000
    assert len(clean_files) == 2
    assert manifest_path.exists()
    assert summary_path.exists()
    assert json.loads(summary_path.read_text(encoding="utf-8"))["accepted_files"] == 2

    for clean_file in clean_files:
        text = clean_file.read_text(encoding="utf-8")
        assert "## Metadata" not in text
        assert "**URL**" not in text

    with manifest_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 3
    assert "char_count" in rows[0]
    assert "source_part" in rows[0]
    assert any(row["reject_reason"] == "too_short" for row in rows)
