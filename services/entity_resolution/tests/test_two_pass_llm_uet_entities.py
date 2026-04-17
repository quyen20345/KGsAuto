import json
from unittest.mock import Mock, patch

import pytest
from sentence_transformers import SentenceTransformer

from services.entity_resolution.matching.two_pass_llm import TwoPassLLMResolver
from services.entity_resolution.tests.test_two_pass_llm_detailed import (
    assert_partition_complete,
    compute_embeddings,
    normalize_for_resolver,
)


@pytest.fixture(scope="module")
def embedding_model():
    return SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")


@pytest.fixture
def provided_entities_cluster():
    return [
        {
            "id": "service_bep_an_trua",
            "labels": ["SERVICE"],
            "properties": {
                "name": "Bếp ăn trưa nội bộ",
                "aliases": [],
                "chunk_id": ["svc_001"],
                "model_extracted": ["gemini-2.5-pro"],
                "description": [
                    "Dịch vụ bếp ăn trưa nội bộ dành cho cán bộ và nhân viên trong trường."
                ],
            },
        },
        {
            "id": "service_ke_hoach_nghi_he",
            "labels": ["PLAN"],
            "properties": {
                "name": "Kế hoạch nghỉ hè",
                "aliases": [],
                "chunk_id": ["svc_002"],
                "model_extracted": ["gemini-2.5-pro"],
                "description": [
                    "Kế hoạch tổ chức nghỉ hè cho công đoàn viên và người lao động."
                ],
            },
        },
        {
            "id": "service_du_xuan_dau_nam",
            "labels": ["EVENT"],
            "properties": {
                "name": "Du xuân đầu năm",
                "aliases": [],
                "chunk_id": ["svc_003"],
                "model_extracted": ["gpt-4.1"],
                "description": [
                    "Chương trình du xuân đầu năm dành cho đoàn viên công đoàn."
                ],
            },
        },
    ]


@pytest.fixture
def has_unit_cluster():
    return [
        {
            "id": "unit_cd_khoi_hieu_bo",
            "labels": ["ORGANIZATIONAL_UNIT", "TRADE_UNION_UNIT"],
            "properties": {
                "name": "Công đoàn Khối Hiệu bộ",
                "aliases": [],
                "chunk_id": ["unit_001"],
                "model_extracted": ["gemini-2.5-pro"],
                "description": [
                    "Công đoàn bộ phận thuộc khối Hiệu bộ của Trường Đại học Công nghệ."
                ],
            },
        },
        {
            "id": "unit_cd_khoa_cntt",
            "labels": ["ORGANIZATIONAL_UNIT", "TRADE_UNION_UNIT"],
            "properties": {
                "name": "Công đoàn Khoa Công nghệ Thông tin",
                "aliases": [],
                "chunk_id": ["unit_002"],
                "model_extracted": ["gemini-2.5-pro"],
                "description": [
                    "Công đoàn bộ phận của Khoa Công nghệ Thông tin thuộc Trường Đại học Công nghệ."
                ],
            },
        },
        {
            "id": "unit_cd_khoa_dtvt",
            "labels": ["ORGANIZATIONAL_UNIT", "TRADE_UNION_UNIT"],
            "properties": {
                "name": "Công đoàn Khoa Điện tử Viễn thông",
                "aliases": [],
                "chunk_id": ["unit_003"],
                "model_extracted": ["gemini-2.5-pro"],
                "description": [
                    "Công đoàn của Khoa Điện tử Viễn thông tại Trường Đại học Công nghệ."
                ],
            },
        },
        {
            "id": "unit_cd_khoa_vlkt_nanotech",
            "labels": ["ORGANIZATIONAL_UNIT", "TRADE_UNION_UNIT"],
            "properties": {
                "name": "Công đoàn Khoa Vật lý kỹ thuật và Công nghệ nano",
                "aliases": [],
                "chunk_id": ["unit_004"],
                "model_extracted": ["gpt-4.1"],
                "description": [
                    "Công đoàn của Khoa Vật lý kỹ thuật và Công nghệ nano tại UET."
                ],
            },
        },
        {
            "id": "unit_cd_khoa_co_hoc_tdh",
            "labels": ["ORGANIZATIONAL_UNIT", "TRADE_UNION_UNIT"],
            "properties": {
                "name": "Công đoàn Khoa Cơ học kỹ thuật và Tự động hóa",
                "aliases": [],
                "chunk_id": ["unit_005"],
                "model_extracted": ["gpt-4.1"],
                "description": [
                    "Công đoàn bộ phận của Khoa Cơ học kỹ thuật và Tự động hóa."
                ],
            },
        },
        {
            "id": "unit_cd_khoa_xdgt",
            "labels": ["ORGANIZATIONAL_UNIT", "TRADE_UNION_UNIT"],
            "properties": {
                "name": "Công đoàn Khoa Công nghệ Xây dựng – Giao thông",
                "aliases": [],
                "chunk_id": ["unit_006"],
                "model_extracted": ["gpt-4.1"],
                "description": [
                    "Công đoàn của Khoa Công nghệ Xây dựng – Giao thông thuộc trường."
                ],
            },
        },
        {
            "id": "unit_lien_chi_doan_nong_nghiep",
            "labels": ["ORGANIZATIONAL_UNIT", "YOUTH_UNION_UNIT"],
            "properties": {
                "name": "Liên chi Đoàn Khoa Công nghệ nông nghiệp",
                "aliases": [],
                "chunk_id": ["unit_007"],
                "model_extracted": ["gpt-4.1"],
                "description": [
                    "Đơn vị Đoàn thanh niên của Khoa Công nghệ nông nghiệp, không phải công đoàn."
                ],
            },
        },
        {
            "id": "unit_cd_vien_hkvt",
            "labels": ["ORGANIZATIONAL_UNIT", "TRADE_UNION_UNIT"],
            "properties": {
                "name": "Công đoàn Viện Công nghệ Hàng không vũ trụ",
                "aliases": [],
                "chunk_id": ["unit_008"],
                "model_extracted": ["claude-3.7-sonnet"],
                "description": [
                    "Công đoàn bộ phận của Viện Công nghệ Hàng không vũ trụ."
                ],
            },
        },
        {
            "id": "unit_vien_ai_uet",
            "labels": ["ORGANIZATIONAL_UNIT", "INSTITUTE"],
            "properties": {
                "name": "Viện Trí tuệ nhân tạo, Trường ĐHCN",
                "aliases": ["Viện Trí tuệ nhân tạo", "AI Institute, UET"],
                "chunk_id": ["unit_009"],
                "model_extracted": ["claude-3.7-sonnet"],
                "description": [
                    "Viện Trí tuệ nhân tạo thuộc Trường Đại học Công nghệ, Đại học Quốc gia Hà Nội."
                ],
            },
        },
        {
            "id": "unit_ban_nu_cong",
            "labels": ["ORGANIZATIONAL_UNIT", "COMMITTEE"],
            "properties": {
                "name": "Ban Nữ công",
                "aliases": [],
                "chunk_id": ["unit_010"],
                "model_extracted": ["gpt-4.1-mini"],
                "description": [
                    "Ban phụ trách công tác nữ công trong công đoàn trường."
                ],
            },
        },
        {
            "id": "unit_ban_van_the",
            "labels": ["ORGANIZATIONAL_UNIT", "COMMITTEE"],
            "properties": {
                "name": "Ban Văn thể",
                "aliases": [],
                "chunk_id": ["unit_011"],
                "model_extracted": ["gpt-4.1-mini"],
                "description": [
                    "Ban phụ trách hoạt động văn nghệ và thể thao của công đoàn."
                ],
            },
        },
        {
            "id": "unit_ban_doi_song",
            "labels": ["ORGANIZATIONAL_UNIT", "COMMITTEE"],
            "properties": {
                "name": "Ban Đời sống",
                "aliases": [],
                "chunk_id": ["unit_012"],
                "model_extracted": ["gpt-4.1-mini"],
                "description": [
                    "Ban phụ trách đời sống và phúc lợi cho đoàn viên công đoàn."
                ],
            },
        },
        {
            "id": "unit_ban_chuyen_mon",
            "labels": ["ORGANIZATIONAL_UNIT", "COMMITTEE"],
            "properties": {
                "name": "Ban Chuyên môn",
                "aliases": [],
                "chunk_id": ["unit_013"],
                "model_extracted": ["gpt-4.1-mini"],
                "description": [
                    "Ban phụ trách các hoạt động chuyên môn trong công đoàn trường."
                ],
            },
        },
        {
            "id": "unit_ban_tai_chinh",
            "labels": ["ORGANIZATIONAL_UNIT", "COMMITTEE"],
            "properties": {
                "name": "Ban Tài chính",
                "aliases": [],
                "chunk_id": ["unit_014"],
                "model_extracted": ["gpt-4.1-mini"],
                "description": [
                    "Ban phụ trách tài chính công đoàn và quản lý kinh phí hoạt động."
                ],
            },
        },
    ]


@pytest.fixture
def subunit_of_cluster():
    return [
        {
            "id": "org_uet_vnu_full",
            "labels": ["ORGANIZATION", "UNIVERSITY"],
            "properties": {
                "name": "Trường Đại học Công nghệ – Đại học Quốc gia Hà Nội (VNU-UET)",
                "aliases": ["VNU-UET", "University of Engineering and Technology, VNU"],
                "chunk_id": ["org_001"],
                "model_extracted": ["gemini-2.5-pro"],
                "description": [
                    "Tên đầy đủ của Trường Đại học Công nghệ thuộc Đại học Quốc gia Hà Nội. Đây là VNU-UET, còn gọi là UET hoặc Trường ĐHCN. University of Engineering and Technology, VNU."
                ],
            },
        },
        {
            "id": "org_uet_vnu_short",
            "labels": ["ORGANIZATION", "UNIVERSITY"],
            "properties": {
                "name": "Trường Đại học Công nghệ, ĐHQGHN",
                "aliases": ["UET", "Trường ĐHCN"],
                "chunk_id": ["org_002"],
                "model_extracted": ["gpt-4.1"],
                "description": [
                    "Biến thể tên viết gọn của Trường Đại học Công nghệ thuộc ĐHQGHN. Chính là VNU-UET, University of Engineering and Technology, VNU, còn gọi là Trường ĐHCN hoặc UET."
                ],
            },
        },
        {
            "id": "org_ban_thuong_vu_dang_uy",
            "labels": ["ORGANIZATIONAL_UNIT", "PARTY_COMMITTEE"],
            "properties": {
                "name": "Ban Thường vụ Đảng ủy Trường ĐHCN",
                "aliases": [],
                "chunk_id": ["org_003"],
                "model_extracted": ["gpt-4.1"],
                "description": [
                    "Ban Thường vụ Đảng ủy của Trường Đại học Công nghệ, là cấp dưới của trường chứ không phải chính trường."
                ],
            },
        },
        {
            "id": "org_cong_doan_dhqghn",
            "labels": ["ORGANIZATION", "TRADE_UNION"],
            "properties": {
                "name": "Công đoàn ĐHQGHN",
                "aliases": ["Công đoàn Đại học Quốc gia Hà Nội"],
                "chunk_id": ["org_004"],
                "model_extracted": ["claude-3.7-sonnet"],
                "description": [
                    "Tổ chức công đoàn cấp Đại học Quốc gia Hà Nội."
                ],
            },
        },
        {
            "id": "org_cong_doan_dhqghn_full",
            "labels": ["ORGANIZATION", "TRADE_UNION"],
            "properties": {
                "name": "Công đoàn Đại học Quốc gia Hà Nội",
                "aliases": ["Công đoàn ĐHQGHN"],
                "chunk_id": ["org_005"],
                "model_extracted": ["claude-3.7-sonnet"],
                "description": [
                    "Tên đầy đủ của Công đoàn ĐHQGHN."
                ],
            },
        },
        {
            "id": "org_cong_doan_gdvn",
            "labels": ["ORGANIZATION", "TRADE_UNION"],
            "properties": {
                "name": "Công đoàn Giáo dục Việt Nam",
                "aliases": [],
                "chunk_id": ["org_006"],
                "model_extracted": ["gpt-4.1-mini"],
                "description": [
                    "Công đoàn ngành giáo dục ở cấp quốc gia, khác với Công đoàn ĐHQGHN."
                ],
            },
        },
    ]


class TestUETEntityCases:
    def test_pass1_should_keep_provides_service_entities_as_singletons(
        self,
        provided_entities_cluster,
        embedding_model,
    ):
        resolver = TwoPassLLMResolver("mock", "mock-model")
        embeddings = compute_embeddings(provided_entities_cluster, embedding_model)
        input_entities = normalize_for_resolver(provided_entities_cluster)

        mock_response = Mock()
        mock_response.content = json.dumps(
            {
                "sub_groups": [],
                "singletons": [node["id"] for node in provided_entities_cluster],
                "confidence": 0.94,
            }
        )

        with patch.object(resolver, "_get_llm_client") as mock_llm:
            mock_llm.return_value.generate.return_value = mock_response
            result = resolver._pass1_subclustering(input_entities, "MIXED")

        expected_ids = {x["id"] for x in provided_entities_cluster}
        assert result["sub_groups"] == []
        assert_partition_complete(result, expected_ids)
        assert set(result["singletons"]) == expected_ids
        assert resolver._validate_subgroups(result, embeddings) is True

    def test_pass1_should_keep_has_unit_entities_separate(
        self,
        has_unit_cluster,
        embedding_model,
    ):
        resolver = TwoPassLLMResolver("mock", "mock-model")
        input_entities = normalize_for_resolver(has_unit_cluster)
        embeddings = compute_embeddings(has_unit_cluster, embedding_model)

        mock_response = Mock()
        mock_response.content = json.dumps(
            {
                "sub_groups": [],
                "singletons": [node["id"] for node in has_unit_cluster],
                "confidence": 0.9,
            }
        )

        with patch.object(resolver, "_get_llm_client") as mock_llm:
            mock_llm.return_value.generate.return_value = mock_response
            result = resolver._pass1_subclustering(input_entities, "ORGANIZATIONAL_UNIT")

        expected_ids = {x["id"] for x in has_unit_cluster}
        assert result["sub_groups"] == []
        assert_partition_complete(result, expected_ids)
        assert set(result["singletons"]) == expected_ids
        assert resolver._validate_subgroups(result, embeddings) is True

    def test_pass1_should_merge_name_variants_but_not_parent_or_peer_orgs(
        self,
        subunit_of_cluster,
        embedding_model,
    ):
        resolver = TwoPassLLMResolver("mock", "mock-model")
        embeddings = compute_embeddings(subunit_of_cluster, embedding_model)
        input_entities = normalize_for_resolver(subunit_of_cluster)

        mock_response = Mock()
        mock_response.content = json.dumps(
            {
                "sub_groups": [
                    {
                        "group_id": "g0",
                        "entity_ids": ["org_uet_vnu_full", "org_uet_vnu_short"],
                        "reasoning": "Hai biến thể tên của cùng Trường Đại học Công nghệ thuộc ĐHQGHN.",
                    },
                    {
                        "group_id": "g1",
                        "entity_ids": ["org_cong_doan_dhqghn", "org_cong_doan_dhqghn_full"],
                        "reasoning": "Tên viết tắt và tên đầy đủ của cùng Công đoàn ĐHQGHN.",
                    },
                ],
                "singletons": [
                    "org_ban_thuong_vu_dang_uy",
                    "org_cong_doan_gdvn",
                ],
                "confidence": 0.92,
            }
        )

        with patch.object(resolver, "_get_llm_client") as mock_llm:
            mock_llm.return_value.generate.return_value = mock_response
            result = resolver._pass1_subclustering(input_entities, "ORGANIZATION")

        expected_ids = {x["id"] for x in subunit_of_cluster}
        assert len(result["sub_groups"]) == 2
        assert_partition_complete(result, expected_ids)

        grouped_pairs = [set(group["entity_ids"]) for group in result["sub_groups"]]
        assert {"org_uet_vnu_full", "org_uet_vnu_short"} in grouped_pairs
        assert {"org_cong_doan_dhqghn", "org_cong_doan_dhqghn_full"} in grouped_pairs
        assert "org_ban_thuong_vu_dang_uy" in result["singletons"]
        assert "org_cong_doan_gdvn" in result["singletons"]
        assert resolver._validate_subgroups(result, embeddings) is True

    def test_full_flow_should_return_two_merges_and_two_singletons_for_subunit_entities(
        self,
        subunit_of_cluster,
        embedding_model,
    ):
        resolver = TwoPassLLMResolver("mock", "mock-model")
        embeddings = compute_embeddings(subunit_of_cluster, embedding_model)
        input_entities = normalize_for_resolver(subunit_of_cluster)

        pass1_response = Mock()
        pass1_response.content = json.dumps(
            {
                "sub_groups": [
                    {
                        "group_id": "g0",
                        "entity_ids": ["org_uet_vnu_full", "org_uet_vnu_short"],
                        "reasoning": "Hai biến thể tên của cùng Trường Đại học Công nghệ thuộc ĐHQGHN.",
                    },
                    {
                        "group_id": "g1",
                        "entity_ids": ["org_cong_doan_dhqghn", "org_cong_doan_dhqghn_full"],
                        "reasoning": "Tên viết tắt và tên đầy đủ của cùng Công đoàn ĐHQGHN.",
                    },
                ],
                "singletons": [
                    "org_ban_thuong_vu_dang_uy",
                    "org_cong_doan_gdvn",
                ],
                "confidence": 0.92,
            }
        )

        pass2_uet = Mock()
        pass2_uet.content = json.dumps(
            {
                "canonical_id": "org_uet_vnu_full",
                "labels": ["ORGANIZATION", "UNIVERSITY"],
                "properties": {
                    "name": "Trường Đại học Công nghệ – Đại học Quốc gia Hà Nội (VNU-UET)",
                    "aliases": [
                        "VNU-UET",
                        "University of Engineering and Technology, VNU",
                        "UET",
                        "Trường ĐHCN",
                        "Trường Đại học Công nghệ, ĐHQGHN",
                    ],
                    "chunk_id": ["org_001", "org_002"],
                    "model_extracted": ["gemini-2.5-pro", "gpt-4.1"],
                    "description": [
                        "Tên đầy đủ của Trường Đại học Công nghệ thuộc Đại học Quốc gia Hà Nội.",
                        "Biến thể tên viết gọn của Trường Đại học Công nghệ thuộc ĐHQGHN.",
                    ],
                },
                "merged_from": ["org_uet_vnu_full", "org_uet_vnu_short"],
            }
        )

        pass2_union = Mock()
        pass2_union.content = json.dumps(
            {
                "canonical_id": "org_cong_doan_dhqghn",
                "labels": ["ORGANIZATION", "TRADE_UNION"],
                "properties": {
                    "name": "Công đoàn ĐHQGHN",
                    "aliases": ["Công đoàn Đại học Quốc gia Hà Nội"],
                    "chunk_id": ["org_004", "org_005"],
                    "model_extracted": ["claude-3.7-sonnet"],
                    "description": [
                        "Tổ chức công đoàn cấp Đại học Quốc gia Hà Nội.",
                        "Tên đầy đủ của Công đoàn ĐHQGHN.",
                    ],
                },
                "merged_from": ["org_cong_doan_dhqghn", "org_cong_doan_dhqghn_full"],
            }
        )

        with patch.object(resolver, "_get_llm_client") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                pass1_response,
                pass2_uet,
                pass2_union,
            ]
            result = resolver.resolve_cluster(input_entities, embeddings, "ORGANIZATION")

        assert len(result) == 4

        uet_merged = next(item for item in result if set(item["merged_from"]) == {"org_uet_vnu_full", "org_uet_vnu_short"})
        union_merged = next(item for item in result if set(item["merged_from"]) == {"org_cong_doan_dhqghn", "org_cong_doan_dhqghn_full"})

        assert uet_merged["properties"]["name"] == "Trường Đại học Công nghệ – Đại học Quốc gia Hà Nội (VNU-UET)"
        assert "Trường ĐHCN" in uet_merged["properties"]["aliases"]
        assert union_merged["properties"]["name"] == "Công đoàn ĐHQGHN"

        singleton_ids = {item["canonical_id"] for item in result if len(item["merged_from"]) == 1}
        assert singleton_ids == {"org_ban_thuong_vu_dang_uy", "org_cong_doan_gdvn"}
