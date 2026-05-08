from __future__ import annotations

from services.entity_resolution.matching.two_pass_llm import TwoPassLLMResolver
from services.entity_resolution.preprocessing.loader import extract_node_records
from services.entity_resolution.utils.canonical_name_selector import select_canonical_name


def test_selects_clear_uet_name_from_mixed_vietnamese_and_english_variants() -> None:
    selected = select_canonical_name(
        [
            "UET",
            "Trường ĐHCN",
            "Trường Đại học Công nghệ",
            "Trường Đại học Công nghệ",
            "Trường Đại học Công nghệ - Đại học Quốc gia Hà Nội",
            "University of Engineering and Technology, VNU",
        ],
        preferred_names=[
            "UET",
            "Trường Đại học Công nghệ - Đại học Quốc gia Hà Nội",
            "University of Engineering and Technology, VNU",
        ],
    )

    assert selected == "Trường Đại học Công nghệ"


def test_selects_frequent_alias_when_single_properties_name_is_verbose() -> None:
    selected = select_canonical_name(
        [
            "Khoa Công nghệ Thông tin thuộc Trường Đại học Công nghệ, Đại học Quốc gia Hà Nội",
            "Khoa Công nghệ Thông tin",
            "Khoa Công nghệ Thông tin",
            "Faculty of Information Technology",
            "FIT",
        ],
        preferred_names=["Khoa Công nghệ Thông tin thuộc Trường Đại học Công nghệ, Đại học Quốc gia Hà Nội"],
    )

    assert selected == "Khoa Công nghệ Thông tin"


def test_prefers_properties_name_when_candidate_quality_is_comparable() -> None:
    selected = select_canonical_name(
        [
            "Đại học Quốc gia Hà Nội",
            "Vietnam National University, Hanoi",
            "VNU",
        ],
        preferred_names=["Đại học Quốc gia Hà Nội"],
    )

    assert selected == "Đại học Quốc gia Hà Nội"


def test_avoids_short_ambiguous_abbreviation_for_organization() -> None:
    selected = select_canonical_name(
        [
            "UET",
            "UET",
            "Trường Đại học Công nghệ",
            "University of Engineering and Technology",
        ],
        preferred_names=["UET", "Trường Đại học Công nghệ"],
    )

    assert selected == "Trường Đại học Công nghệ"


def test_avoids_long_descriptive_sentence() -> None:
    selected = select_canonical_name(
        [
            "Khoa Công nghệ Thông tin",
            "Khoa Công nghệ Thông tin là đơn vị đào tạo về công nghệ thông tin thuộc Trường Đại học Công nghệ",
            "FIT",
        ],
        preferred_names=[
            "Khoa Công nghệ Thông tin",
            "Khoa Công nghệ Thông tin là đơn vị đào tạo về công nghệ thông tin thuộc Trường Đại học Công nghệ",
        ],
    )

    assert selected == "Khoa Công nghệ Thông tin"


def test_selects_person_name_without_title_or_abbreviation() -> None:
    selected = select_canonical_name(
        [
            "TS. Nguyễn Văn An",
            "Nguyễn Văn An",
            "Nguyễn Văn An",
            "Dr. Nguyen Van An",
            "NVA",
            "N. V. An",
        ],
        preferred_names=["TS. Nguyễn Văn An", "Nguyễn Văn An"],
    )

    assert selected == "Nguyễn Văn An"


def test_normalizes_whitespace_for_frequency_and_display() -> None:
    selected = select_canonical_name(
        [
            "Trường   Đại học Công nghệ",
            "Trường Đại học Công nghệ",
            "Trường Đại học Công nghệ - Đại học Quốc gia Hà Nội",
        ],
        preferred_names=["Trường   Đại học Công nghệ"],
    )

    assert selected == "Trường Đại học Công nghệ"


def test_empty_candidates_return_empty_name() -> None:
    assert select_canonical_name([], preferred_names=[]) == ""
    assert select_canonical_name(["", "   "], preferred_names=[""]) == ""


def test_tie_break_is_deterministic() -> None:
    first = select_canonical_name(
        ["Khoa Toán", "Khoa Vật lý"],
        preferred_names=[],
    )
    second = select_canonical_name(
        ["Khoa Vật lý", "Khoa Toán"],
        preferred_names=[],
    )

    assert first == second


def test_extract_node_records_uses_scored_name_selection() -> None:
    records = extract_node_records(
        {
            "a.json": {
                "nodes": [
                    {
                        "id": "node_uet",
                        "labels": ["ORGANIZATION"],
                        "properties": {
                            "name": "UET",
                            "aliases": ["Trường Đại học Công nghệ", "Trường ĐHCN"],
                        },
                    }
                ]
            },
            "b.json": {
                "nodes": [
                    {
                        "id": "node_uet",
                        "labels": ["ORGANIZATION"],
                        "properties": {
                            "name": "Trường Đại học Công nghệ - Đại học Quốc gia Hà Nội",
                            "aliases": ["University of Engineering and Technology, VNU"],
                        },
                    }
                ]
            },
            "c.json": {
                "nodes": [
                    {
                        "id": "node_uet",
                        "labels": ["UNIVERSITY"],
                        "properties": {
                            "name": "Trường Đại học Công nghệ",
                        },
                    }
                ]
            },
        }
    )

    assert len(records) == 1
    assert records[0].properties["name"] == "Trường Đại học Công nghệ"


def test_rule_based_merge_falls_back_to_first_node_id_when_no_name_exists() -> None:
    resolver = TwoPassLLMResolver("mock", "mock-model")
    result = resolver._merge_entities_rule_based(
        [
            {
                "node_id": "node_without_name",
                "payload": {
                    "labels": ["ORGANIZATION"],
                    "properties": {"aliases": []},
                },
            }
        ]
    )

    assert result["properties"].get("name") is None
    assert result["canonical_id"] == "node_without_name"


def test_rule_based_merge_uses_scored_name_for_canonical_id() -> None:
    resolver = TwoPassLLMResolver("mock", "mock-model")
    result = resolver._merge_entities_rule_based(
        [
            {
                "node_id": "node_short",
                "payload": {
                    "labels": ["ORGANIZATION"],
                    "properties": {
                        "name": "UET",
                        "aliases": ["Trường Đại học Công nghệ", "Trường ĐHCN"],
                    },
                },
            },
            {
                "node_id": "node_verbose",
                "payload": {
                    "labels": ["ORGANIZATION"],
                    "properties": {
                        "name": "Trường Đại học Công nghệ - Đại học Quốc gia Hà Nội",
                        "aliases": ["University of Engineering and Technology, VNU"],
                    },
                },
            },
            {
                "node_id": "node_clear",
                "payload": {
                    "labels": ["UNIVERSITY"],
                    "properties": {
                        "name": "Trường Đại học Công nghệ",
                    },
                },
            },
        ]
    )

    assert result["properties"]["name"] == "Trường Đại học Công nghệ"
    assert result["canonical_id"] == "node_truong_ai_hoc_cong_nghe"
