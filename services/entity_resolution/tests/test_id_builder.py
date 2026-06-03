"""Tests for ID builder utility."""

import pytest

from services.entity_resolution.utils.id_builder import (
    build_canonical_id,
    ensure_unique_canonical_id,
)


class TestBuildCanonicalId:
    """Tests for build_canonical_id function."""

    def test_simple_name(self):
        """Test simple name without special characters."""
        assert build_canonical_id("Test") == "node_test"

    def test_vietnamese_diacritics(self):
        """Test Vietnamese names with diacritics."""
        assert build_canonical_id("Xuân Thủy") == "node_xuan_thuy"
        assert build_canonical_id("Hà Nội") == "node_ha_noi"
        assert build_canonical_id("Trường Đại học Công nghệ") == "node_truong_dai_hoc_cong_nghe"
        assert build_canonical_id("Đảng ủy") == "node_dang_uy"
        assert build_canonical_id("Đại học Quốc gia Hà Nội") == "node_dai_hoc_quoc_gia_ha_noi"
        assert build_canonical_id("Đồ họa máy tính") == "node_do_hoa_may_tinh"

    def test_complex_address(self):
        """Test complex address with numbers and special characters."""
        result = build_canonical_id("144 Xuân Thủy, Cầu Giấy, Hà Nội")
        assert result == "node_144_xuan_thuy_cau_giay_ha_noi"

    def test_special_characters(self):
        """Test names with special characters."""
        assert build_canonical_id("Test-Name") == "node_test-name"
        assert build_canonical_id("Test_Name") == "node_test_name"
        assert build_canonical_id("Test & Name") == "node_test_name"
        assert build_canonical_id("Test (Name)") == "node_test_name"

    def test_multiple_spaces(self):
        """Test names with multiple spaces."""
        assert build_canonical_id("Test  Name") == "node_test_name"
        assert build_canonical_id("Test   Multiple   Spaces") == "node_test_multiple_spaces"

    def test_leading_trailing_spaces(self):
        """Test names with leading/trailing spaces."""
        assert build_canonical_id("  Test  ") == "node_test"
        assert build_canonical_id("  Test Name  ") == "node_test_name"

    def test_empty_string(self):
        """Test empty string."""
        assert build_canonical_id("") == "node_unknown"

    def test_only_special_characters(self):
        """Test string with only special characters."""
        assert build_canonical_id("!!!") == "node_unknown"
        assert build_canonical_id("@#$%") == "node_unknown"

    def test_very_long_name(self):
        """Test very long name gets truncated."""
        long_name = "A" * 250
        result = build_canonical_id(long_name)
        assert result.startswith("node_")
        assert len(result) <= 205  # node_ (5) + 200 chars

    def test_unicode_normalization(self):
        """Test Unicode normalization."""
        # Different Unicode representations of same character
        assert build_canonical_id("café") == build_canonical_id("café")

    def test_numbers_preserved(self):
        """Test that numbers are preserved."""
        assert build_canonical_id("Room 123") == "node_room_123"
        assert build_canonical_id("2024 Report") == "node_2024_report"

    def test_lowercase_conversion(self):
        """Test lowercase conversion."""
        assert build_canonical_id("TEST") == "node_test"
        assert build_canonical_id("TeSt NaMe") == "node_test_name"

    def test_collapse_underscores(self):
        """Test collapsing multiple underscores."""
        assert build_canonical_id("Test___Name") == "node_test_name"
        assert build_canonical_id("Test _ _ Name") == "node_test_name"


class TestEnsureUniqueCanonicalId:
    """Tests for ensure_unique_canonical_id function."""

    def test_unique_id(self):
        """Test ID that doesn't exist in set."""
        existing = {"node_test1", "node_test2"}
        result = ensure_unique_canonical_id("node_test3", existing)
        assert result == "node_test3"

    def test_duplicate_id(self):
        """Test ID that already exists."""
        existing = {"node_test"}
        result = ensure_unique_canonical_id("node_test", existing)
        assert result == "node_test_2"

    def test_multiple_duplicates(self):
        """Test ID with multiple duplicates."""
        existing = {"node_test", "node_test_2"}
        result = ensure_unique_canonical_id("node_test", existing)
        assert result == "node_test_3"

    def test_sequential_duplicates(self):
        """Test sequential duplicate handling."""
        existing = {"node_test", "node_test_2", "node_test_3", "node_test_4"}
        result = ensure_unique_canonical_id("node_test", existing)
        assert result == "node_test_5"

    def test_empty_existing_set(self):
        """Test with empty existing set."""
        existing = set()
        result = ensure_unique_canonical_id("node_test", existing)
        assert result == "node_test"

    def test_gap_in_sequence(self):
        """Test with gap in sequence (should still use next number)."""
        existing = {"node_test", "node_test_3"}
        result = ensure_unique_canonical_id("node_test", existing)
        assert result == "node_test_2"


class TestIntegration:
    """Integration tests combining both functions."""

    def test_build_and_ensure_unique(self):
        """Test building ID and ensuring uniqueness."""
        existing = set()

        # First entity
        id1 = build_canonical_id("Xuân Thủy")
        id1 = ensure_unique_canonical_id(id1, existing)
        existing.add(id1)
        assert id1 == "node_xuan_thuy"

        # Second entity with same name
        id2 = build_canonical_id("Xuân Thủy")
        id2 = ensure_unique_canonical_id(id2, existing)
        existing.add(id2)
        assert id2 == "node_xuan_thuy_2"

        # Third entity with different name
        id3 = build_canonical_id("Hà Nội")
        id3 = ensure_unique_canonical_id(id3, existing)
        existing.add(id3)
        assert id3 == "node_ha_noi"

    def test_collision_from_different_names(self):
        """Test collision when different names generate same ID."""
        existing = set()

        # Names that might generate similar IDs after sanitization
        id1 = build_canonical_id("Test Name")
        id1 = ensure_unique_canonical_id(id1, existing)
        existing.add(id1)

        id2 = build_canonical_id("Test-Name")
        id2 = ensure_unique_canonical_id(id2, existing)
        existing.add(id2)

        # Both should be unique
        assert id1 != id2
        assert len(existing) == 2
