import json
import logging
from unittest.mock import Mock, patch

import numpy as np
import pytest
from sentence_transformers import SentenceTransformer

from services.entity_resolution.matching.two_pass_llm import TwoPassLLMResolver


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(name)s - %(message)s"
)


# =========================================================
# Helpers
# =========================================================

def normalize_for_resolver(nodes):
    """
    Convert NEW schema:
      - id
      - labels
      - properties
    to legacy schema if resolver internals still expect:
      - node_id
      - payload.labels
      - payload.properties

    Remove this helper once resolver uses the new schema directly.
    """
    normalized = []
    for node in nodes:
        normalized.append({
            "node_id": node["id"],
            "payload": {
                "labels": node.get("labels", []),
                "properties": node.get("properties", {})
            }
        })
    return normalized


def build_embedding_text(node):
    props = node.get("properties", {})
    name = props.get("name", "") or ""
    aliases = props.get("aliases", []) or []
    descriptions = props.get("description", []) or []
    if isinstance(descriptions, str):
        descriptions = [descriptions]
    return " ".join([name] + aliases + descriptions).strip()


def compute_embeddings(nodes, embedding_model):
    embeddings = {}
    for node in nodes:
        vector = embedding_model.encode(
            build_embedding_text(node),
            convert_to_numpy=True
        )
        embeddings[node["id"]] = vector.tolist()
    return embeddings


def cosine_sim(v1, v2):
    a = np.array(v1)
    b = np.array(v2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def assert_partition_complete(result, expected_ids):
    covered = set()
    for group in result["sub_groups"]:
        for eid in group["entity_ids"]:
            assert eid not in covered, f"Duplicate entity across groups/singletons: {eid}"
            covered.add(eid)

    for eid in result["singletons"]:
        assert eid not in covered, f"Duplicate singleton/group entity: {eid}"
        covered.add(eid)

    assert covered == expected_ids, f"Coverage mismatch. covered={covered}, expected={expected_ids}"


# =========================================================
# Fixtures
# =========================================================

@pytest.fixture(scope="module")
def embedding_model():
    print("\n[SETUP] Loading embedding model: paraphrase-multilingual-mpnet-base-v2")
    return SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")


@pytest.fixture
def person_multi_subgroup_cluster():
    """
    Cluster này có:
    - Subgroup A: cùng 1 người, khác labels / khác ngôn ngữ / khác cách gọi
    - Subgroup B: cùng 1 người khác nhưng trùng tên gần hoàn toàn
    - Hard negative: tên rất giống nhưng là người khác
    - Singleton rõ ràng

    Mọi thông tin ngữ cảnh đều nằm trong description.
    """
    return [
        {
            "id": "node_nguyen_van_an_doc001",
            "labels": ["PERSON", "LECTURER"],
            "properties": {
                "name": "Nguyễn Văn An",
                "aliases": ["NVA", "TS. Nguyễn Văn An"],
                "chunk_id": ["doc_001"],
                "model_extracted": ["gemini-2.5-pro"],
                "description": [
                    "Giảng viên khoa Công nghệ Thông tin tại Trường Đại học Công nghệ, ĐHQGHN. "
                    "Chuyên về AI. Email liên hệ: nva@vnu.edu.vn."
                ]
            }
        },
        {
            "id": "node_dr_nguyen_van_an_doc002",
            "labels": ["PERSON", "RESEARCHER"],
            "properties": {
                "name": "Dr. Nguyen Van An",
                "aliases": ["Nguyen Van An", "NVA"],
                "chunk_id": ["doc_002"],
                "model_extracted": ["gpt-4.1"],
                "description": [
                    "Researcher at Faculty of Information Technology, University of Engineering and Technology, VNU. "
                    "Works on artificial intelligence. Contact email: nva@vnu.edu.vn."
                ]
            }
        },
        {
            "id": "node_nv_an_doc003",
            "labels": ["PERSON"],
            "properties": {
                "name": "N. V. An",
                "aliases": ["Nguyễn Văn An"],
                "chunk_id": ["doc_003"],
                "model_extracted": ["gpt-4.1-mini"],
                "description": [
                    "AI lecturer at VNU-UET. Common full name variant is Nguyen Van An. "
                    "Same person referenced in faculty profile."
                ]
            }
        },
        {
            "id": "node_nguyen_van_an_staff_doc006",
            "labels": ["PERSON", "STAFF"],
            "properties": {
                "name": "TS. Nguyễn Văn An",
                "aliases": ["Nguyễn Văn An", "Dr. Nguyen Van An"],
                "chunk_id": ["doc_006"],
                "model_extracted": ["claude-3.7-sonnet"],
                "description": [
                    "Academic staff at Trường Đại học Công nghệ, ĐHQGHN. "
                    "Works on AI and data mining. Same contact email nva@vnu.edu.vn."
                ]
            }
        },
        {
            "id": "node_nguyen_van_an_student_doc004",
            "labels": ["PERSON", "STUDENT"],
            "properties": {
                "name": "Nguyễn Văn An",
                "aliases": ["Nguyen Van An"],
                "chunk_id": ["doc_004"],
                "model_extracted": ["gemini-2.5-pro"],
                "description": [
                    "Sinh viên năm 3 ngành Công nghệ Thông tin tại Đại học Bách Khoa Hà Nội. "
                    "Email sinh viên: an.nguyen22@hust.edu.vn."
                ]
            }
        },
        {
            "id": "node_nguyen_van_an_undergrad_doc005",
            "labels": ["PERSON"],
            "properties": {
                "name": "Nguyen Van An",
                "aliases": ["N. V. An"],
                "chunk_id": ["doc_005"],
                "model_extracted": ["gpt-4.1"],
                "description": [
                    "Undergraduate student in information technology at Hanoi University of Science and Technology. "
                    "Likely the same student profile as the HUST student named Nguyen Van An."
                ]
            }
        },
        {
            "id": "node_nguyen_van_an_accent_doc007",
            "labels": ["PERSON", "LECTURER"],
            "properties": {
                "name": "Nguyễn Văn Ân",
                "aliases": ["Nguyen Van An"],
                "chunk_id": ["doc_007"],
                "model_extracted": ["gpt-4.1"],
                "description": [
                    "Giảng viên về hệ thống thông tin. Công tác tại một đơn vị khác, không phải Trường Đại học Công nghệ, ĐHQGHN. "
                    "Không có bằng chứng cho thấy cùng email hay cùng hồ sơ với Nguyễn Văn An ở VNU-UET."
                ]
            }
        },
        {
            "id": "node_tran_thi_binh_doc008",
            "labels": ["PERSON", "STUDENT"],
            "properties": {
                "name": "Trần Thị Bình",
                "aliases": ["TTB"],
                "chunk_id": ["doc_008"],
                "model_extracted": ["gemini-2.5-pro"],
                "description": [
                    "Sinh viên năm 3 chuyên ngành Công nghệ Thông tin."
                ]
            }
        },
    ]


@pytest.fixture
def organizational_unit_multi_subgroup_cluster():
    """
    Cluster để test:
    - cùng object nhưng labels khác nhau
    - cùng tên nhưng khác tổ chức
    - gần nhau theo hierarchy nhưng không phải cùng object
    """
    return [
        {
            "id": "node_khoa_cntt_doc101",
            "labels": ["ORGANIZATIONAL_UNIT", "FACULTY"],
            "properties": {
                "name": "Khoa Công nghệ Thông tin",
                "aliases": ["Khoa CNTT", "Faculty of Information Technology"],
                "chunk_id": ["doc_101"],
                "model_extracted": ["gemini-2.5-pro"],
                "description": [
                    "Đơn vị đào tạo về công nghệ thông tin thuộc Trường Đại học Công nghệ, ĐHQGHN."
                ]
            }
        },
        {
            "id": "node_fit_doc102",
            "labels": ["ORGANIZATIONAL_UNIT"],
            "properties": {
                "name": "Faculty of Information Technology",
                "aliases": ["FIT", "Khoa CNTT"],
                "chunk_id": ["doc_102"],
                "model_extracted": ["gpt-4.1"],
                "description": [
                    "Faculty of Information Technology under University of Engineering and Technology, VNU. "
                    "This is the English naming variant of Khoa Cong nghe Thong tin at UET."
                ]
            }
        },
        {
            "id": "node_fit_uet_doc103",
            "labels": ["EDUCATIONAL_INSTITUTION"],
            "properties": {
                "name": "FIT - UET",
                "aliases": ["Faculty of IT", "Khoa CNTT"],
                "chunk_id": ["doc_103"],
                "model_extracted": ["claude-3.7-sonnet"],
                "description": [
                    "IT faculty under VNU-UET. Refers to the same faculty commonly called Khoa CNTT."
                ]
            }
        },
        {
            "id": "node_khoa_cntt_hust_doc104",
            "labels": ["ORGANIZATIONAL_UNIT", "FACULTY"],
            "properties": {
                "name": "Khoa Công nghệ Thông tin",
                "aliases": ["Khoa CNTT"],
                "chunk_id": ["doc_104"],
                "model_extracted": ["gemini-2.5-pro"],
                "description": [
                    "Đơn vị đào tạo CNTT tại Đại học Bách Khoa Hà Nội. "
                    "Tên giống nhưng là tổ chức khác với Khoa CNTT của UET."
                ]
            }
        },
        {
            "id": "node_bm_khmt_doc105",
            "labels": ["ORGANIZATIONAL_UNIT", "DEPARTMENT"],
            "properties": {
                "name": "Bộ môn Khoa học Máy tính",
                "aliases": ["Computer Science Department"],
                "chunk_id": ["doc_105"],
                "model_extracted": ["gpt-4.1"],
                "description": [
                    "Bộ môn trực thuộc Khoa Công nghệ Thông tin tại Trường Đại học Công nghệ, ĐHQGHN. "
                    "Có quan hệ cấp dưới với Khoa CNTT, không phải cùng một đơn vị."
                ]
            }
        },
        {
            "id": "node_cs_department_doc106",
            "labels": ["ORGANIZATIONAL_UNIT", "DEPARTMENT"],
            "properties": {
                "name": "Computer Science Department",
                "aliases": ["Bộ môn Khoa học Máy tính"],
                "chunk_id": ["doc_106"],
                "model_extracted": ["gpt-4.1-mini"],
                "description": [
                    "Department under Faculty of Information Technology at UET. "
                    "English variant of Bo mon Khoa hoc May tinh."
                ]
            }
        },
    ]


# =========================================================
# Pass 1 tests
# =========================================================

class TestPass1NewSchemaDescriptionDriven:

    def test_pass1_person_cluster_should_split_into_multiple_subgroups(
        self,
        person_multi_subgroup_cluster,
        embedding_model,
        caplog
    ):
        caplog.set_level(logging.INFO)

        resolver = TwoPassLLMResolver("mock", "mock-model")
        embeddings = compute_embeddings(person_multi_subgroup_cluster, embedding_model)
        input_entities = normalize_for_resolver(person_multi_subgroup_cluster)

        mock_response = Mock()
        mock_response.content = json.dumps({
            "sub_groups": [
                {
                    "group_id": "g0",
                    "entity_ids": [
                        "node_nguyen_van_an_doc001",
                        "node_dr_nguyen_van_an_doc002",
                        "node_nv_an_doc003",
                        "node_nguyen_van_an_staff_doc006"
                    ],
                    "reasoning": (
                        "Cùng tham chiếu giảng viên/nghiên cứu viên Nguyễn Văn An tại VNU-UET; "
                        "description cho thấy cùng đơn vị, cùng email, cùng lĩnh vực AI."
                    )
                },
                {
                    "group_id": "g1",
                    "entity_ids": [
                        "node_nguyen_van_an_student_doc004",
                        "node_nguyen_van_an_undergrad_doc005"
                    ],
                    "reasoning": (
                        "Cùng tham chiếu sinh viên Nguyễn Văn An tại HUST; "
                        "description đều nói đây là hồ sơ sinh viên/undergraduate cùng trường."
                    )
                }
            ],
            "singletons": [
                "node_nguyen_van_an_accent_doc007",
                "node_tran_thi_binh_doc008"
            ],
            "confidence": 0.91
        })

        with patch.object(resolver, "_get_llm_client") as mock_llm:
            mock_llm.return_value.generate.return_value = mock_response
            result = resolver._pass1_subclustering(input_entities, "PERSON")

        expected_ids = {x["id"] for x in person_multi_subgroup_cluster}
        assert len(result["sub_groups"]) == 2
        assert_partition_complete(result, expected_ids)

        g0 = next(g for g in result["sub_groups"] if g["group_id"] == "g0")
        g1 = next(g for g in result["sub_groups"] if g["group_id"] == "g1")

        assert set(g0["entity_ids"]) == {
            "node_nguyen_van_an_doc001",
            "node_dr_nguyen_van_an_doc002",
            "node_nv_an_doc003",
            "node_nguyen_van_an_staff_doc006"
        }
        assert set(g1["entity_ids"]) == {
            "node_nguyen_van_an_student_doc004",
            "node_nguyen_van_an_undergrad_doc005"
        }
        assert set(result["singletons"]) == {
            "node_nguyen_van_an_accent_doc007",
            "node_tran_thi_binh_doc008"
        }

    def test_pass1_org_cluster_should_split_multiple_groups_and_keep_hard_negative_out(
        self,
        organizational_unit_multi_subgroup_cluster,
        embedding_model,
        caplog
    ):
        caplog.set_level(logging.INFO)

        resolver = TwoPassLLMResolver("mock", "mock-model")
        embeddings = compute_embeddings(organizational_unit_multi_subgroup_cluster, embedding_model)
        input_entities = normalize_for_resolver(organizational_unit_multi_subgroup_cluster)

        mock_response = Mock()
        mock_response.content = json.dumps({
            "sub_groups": [
                {
                    "group_id": "g0",
                    "entity_ids": [
                        "node_khoa_cntt_doc101",
                        "node_fit_doc102",
                        "node_fit_uet_doc103"
                    ],
                    "reasoning": (
                        "Cùng là Khoa CNTT/FIT của UET; khác ngôn ngữ và labels nhưng description chỉ cùng đơn vị."
                    )
                },
                {
                    "group_id": "g1",
                    "entity_ids": [
                        "node_bm_khmt_doc105",
                        "node_cs_department_doc106"
                    ],
                    "reasoning": (
                        "Cùng là Bộ môn Khoa học Máy tính; description nói rõ đây là English/Vietnamese variants."
                    )
                }
            ],
            "singletons": [
                "node_khoa_cntt_hust_doc104"
            ],
            "confidence": 0.90
        })

        with patch.object(resolver, "_get_llm_client") as mock_llm:
            mock_llm.return_value.generate.return_value = mock_response
            result = resolver._pass1_subclustering(input_entities, "ORGANIZATIONAL_UNIT")

        expected_ids = {x["id"] for x in organizational_unit_multi_subgroup_cluster}
        assert len(result["sub_groups"]) == 2
        assert_partition_complete(result, expected_ids)

        grouped_ids = set()
        for g in result["sub_groups"]:
            grouped_ids.update(g["entity_ids"])

        assert "node_khoa_cntt_hust_doc104" not in grouped_ids
        assert "node_khoa_cntt_hust_doc104" in result["singletons"]


# =========================================================
# Pass 2 tests
# =========================================================

class TestPass2NewSchemaDescriptionDriven:

    def test_pass2_should_merge_same_object_even_with_label_mismatch(
        self,
        organizational_unit_multi_subgroup_cluster,
        caplog
    ):
        caplog.set_level(logging.INFO)

        resolver = TwoPassLLMResolver("mock", "mock-model")
        input_entities = normalize_for_resolver(organizational_unit_multi_subgroup_cluster)

        sub_group = {
            "group_id": "g0",
            "entity_ids": [
                "node_khoa_cntt_doc101",
                "node_fit_doc102",
                "node_fit_uet_doc103"
            ],
            "reasoning": "Cùng là Khoa CNTT/FIT của UET"
        }

        mock_response = Mock()
        mock_response.content = json.dumps({
            "canonical_id": "node_khoa_cntt_doc101",
            "labels": ["ORGANIZATIONAL_UNIT", "FACULTY", "EDUCATIONAL_INSTITUTION"],
            "properties": {
                "name": "Khoa Công nghệ Thông tin",
                "aliases": [
                    "Khoa CNTT",
                    "Faculty of Information Technology",
                    "FIT",
                    "FIT - UET",
                    "Faculty of IT"
                ],
                "chunk_id": ["doc_101", "doc_102", "doc_103"],
                "model_extracted": ["gemini-2.5-pro", "gpt-4.1", "claude-3.7-sonnet"],
                "description": [
                    "Đơn vị đào tạo về công nghệ thông tin thuộc Trường Đại học Công nghệ, ĐHQGHN.",
                    "Faculty of Information Technology under University of Engineering and Technology, VNU.",
                    "IT faculty under VNU-UET. Refers to the same faculty commonly called Khoa CNTT."
                ]
            },
            "merged_from": [
                "node_khoa_cntt_doc101",
                "node_fit_doc102",
                "node_fit_uet_doc103"
            ]
        })

        with patch.object(resolver, "_get_llm_client") as mock_llm:
            mock_llm.return_value.generate.return_value = mock_response
            result = resolver._pass2_merge(sub_group, input_entities, "ORGANIZATIONAL_UNIT")

        assert result["canonical_id"] == "node_khoa_cntt_doc101"
        assert set(result["merged_from"]) == {
            "node_khoa_cntt_doc101",
            "node_fit_doc102",
            "node_fit_uet_doc103"
        }
        assert set(result["labels"]) == {
            "ORGANIZATIONAL_UNIT",
            "FACULTY",
            "EDUCATIONAL_INSTITUTION"
        }
        assert "FIT" in result["properties"]["aliases"]
        assert "Faculty of IT" in result["properties"]["aliases"]


# =========================================================
# Validation / hard negative tests
# =========================================================

class TestHardNegativeNewSchemaDescriptionDriven:

    def test_validate_should_fail_for_same_name_but_different_real_world_person(
        self,
        person_multi_subgroup_cluster,
        embedding_model,
        caplog
    ):
        caplog.set_level(logging.INFO)

        resolver = TwoPassLLMResolver("mock", "mock-model")
        embeddings = compute_embeddings(person_multi_subgroup_cluster, embedding_model)

        invalid_pass1_result = {
            "sub_groups": [
                {
                    "group_id": "g0",
                    "entity_ids": [
                        "node_nguyen_van_an_doc001",
                        "node_nguyen_van_an_student_doc004"
                    ],
                    "reasoning": "Tên giống nhau nên gộp"
                }
            ],
            "singletons": [
                "node_dr_nguyen_van_an_doc002",
                "node_nv_an_doc003",
                "node_nguyen_van_an_undergrad_doc005",
                "node_nguyen_van_an_staff_doc006",
                "node_nguyen_van_an_accent_doc007",
                "node_tran_thi_binh_doc008"
            ],
            "confidence": 0.52
        }

        is_valid = resolver._validate_subgroups(invalid_pass1_result, embeddings)

        sim = cosine_sim(
            embeddings["node_nguyen_van_an_doc001"],
            embeddings["node_nguyen_van_an_student_doc004"]
        )
        print(f"\nSimilarity lecturer-VNU vs student-HUST: {sim:.4f}")

        # Đây là assertion business-logic mong muốn.
        # Nếu fail, đó là dấu hiệu validator hiện tại chưa tận dụng context trong description đủ tốt.
        assert is_valid is False

    def test_pass1_should_not_merge_same_name_but_different_org_units(
        self,
        organizational_unit_multi_subgroup_cluster,
        embedding_model,
        caplog
    ):
        caplog.set_level(logging.INFO)

        resolver = TwoPassLLMResolver("mock", "mock-model")
        embeddings = compute_embeddings(organizational_unit_multi_subgroup_cluster, embedding_model)
        input_entities = normalize_for_resolver(organizational_unit_multi_subgroup_cluster)

        mock_response = Mock()
        mock_response.content = json.dumps({
            "sub_groups": [
                {
                    "group_id": "g0",
                    "entity_ids": [
                        "node_khoa_cntt_doc101",
                        "node_fit_doc102",
                        "node_fit_uet_doc103"
                    ],
                    "reasoning": "Cùng Khoa CNTT/FIT của UET"
                },
                {
                    "group_id": "g1",
                    "entity_ids": [
                        "node_bm_khmt_doc105",
                        "node_cs_department_doc106"
                    ],
                    "reasoning": "Cùng Bộ môn Khoa học Máy tính"
                }
            ],
            "singletons": [
                "node_khoa_cntt_hust_doc104"
            ],
            "confidence": 0.88
        })

        with patch.object(resolver, "_get_llm_client") as mock_llm:
            mock_llm.return_value.generate.return_value = mock_response
            result = resolver._pass1_subclustering(input_entities, "ORGANIZATIONAL_UNIT")

        grouped_ids = set()
        for g in result["sub_groups"]:
            grouped_ids.update(g["entity_ids"])

        assert "node_khoa_cntt_hust_doc104" not in grouped_ids
        assert "node_khoa_cntt_hust_doc104" in result["singletons"]


# =========================================================
# Full integration test
# =========================================================

class TestFullFlowNewSchemaDescriptionDriven:

    def test_full_flow_person_cluster(
        self,
        person_multi_subgroup_cluster,
        embedding_model,
        caplog
    ):
        caplog.set_level(logging.INFO)

        resolver = TwoPassLLMResolver("mock", "mock-model")
        embeddings = compute_embeddings(person_multi_subgroup_cluster, embedding_model)
        input_entities = normalize_for_resolver(person_multi_subgroup_cluster)

        pass1_response = Mock()
        pass1_response.content = json.dumps({
            "sub_groups": [
                {
                    "group_id": "g0",
                    "entity_ids": [
                        "node_nguyen_van_an_doc001",
                        "node_dr_nguyen_van_an_doc002",
                        "node_nv_an_doc003",
                        "node_nguyen_van_an_staff_doc006"
                    ],
                    "reasoning": (
                        "Cùng một giảng viên/nghiên cứu viên Nguyễn Văn An tại VNU-UET; "
                        "description nói cùng email, cùng lĩnh vực AI, cùng tổ chức."
                    )
                },
                {
                    "group_id": "g1",
                    "entity_ids": [
                        "node_nguyen_van_an_student_doc004",
                        "node_nguyen_van_an_undergrad_doc005"
                    ],
                    "reasoning": (
                        "Cùng một sinh viên Nguyễn Văn An tại HUST."
                    )
                }
            ],
            "singletons": [
                "node_nguyen_van_an_accent_doc007",
                "node_tran_thi_binh_doc008"
            ],
            "confidence": 0.92
        })

        pass2_response_g0 = Mock()
        pass2_response_g0.content = json.dumps({
            "canonical_id": "node_nguyen_van_an_doc001",
            "labels": ["PERSON", "LECTURER", "RESEARCHER", "STAFF"],
            "properties": {
                "name": "Nguyễn Văn An",
                "aliases": [
                    "NVA",
                    "TS. Nguyễn Văn An",
                    "Dr. Nguyen Van An",
                    "Nguyen Van An",
                    "N. V. An"
                ],
                "chunk_id": ["doc_001", "doc_002", "doc_003", "doc_006"],
                "model_extracted": [
                    "gemini-2.5-pro",
                    "gpt-4.1",
                    "gpt-4.1-mini",
                    "claude-3.7-sonnet"
                ],
                "description": [
                    "Giảng viên khoa Công nghệ Thông tin tại Trường Đại học Công nghệ, ĐHQGHN. Chuyên về AI. Email liên hệ: nva@vnu.edu.vn.",
                    "Researcher at Faculty of Information Technology, University of Engineering and Technology, VNU. Works on artificial intelligence. Contact email: nva@vnu.edu.vn.",
                    "AI lecturer at VNU-UET. Common full name variant is Nguyen Van An. Same person referenced in faculty profile.",
                    "Academic staff at Trường Đại học Công nghệ, ĐHQGHN. Works on AI and data mining. Same contact email nva@vnu.edu.vn."
                ]
            },
            "merged_from": [
                "node_nguyen_van_an_doc001",
                "node_dr_nguyen_van_an_doc002",
                "node_nv_an_doc003",
                "node_nguyen_van_an_staff_doc006"
            ]
        })

        pass2_response_g1 = Mock()
        pass2_response_g1.content = json.dumps({
            "canonical_id": "node_nguyen_van_an_student_doc004",
            "labels": ["PERSON", "STUDENT"],
            "properties": {
                "name": "Nguyễn Văn An",
                "aliases": [
                    "Nguyen Van An",
                    "N. V. An"
                ],
                "chunk_id": ["doc_004", "doc_005"],
                "model_extracted": ["gemini-2.5-pro", "gpt-4.1"],
                "description": [
                    "Sinh viên năm 3 ngành Công nghệ Thông tin tại Đại học Bách Khoa Hà Nội. Email sinh viên: an.nguyen22@hust.edu.vn.",
                    "Undergraduate student in information technology at Hanoi University of Science and Technology. Likely the same student profile as the HUST student named Nguyen Van An."
                ]
            },
            "merged_from": [
                "node_nguyen_van_an_student_doc004",
                "node_nguyen_van_an_undergrad_doc005"
            ]
        })

        with patch.object(resolver, "_get_llm_client") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                pass1_response,
                pass2_response_g0,
                pass2_response_g1
            ]
            result = resolver.resolve_cluster(input_entities, embeddings, "PERSON")

        assert len(result) == 4  # 2 merged + 2 singletons

        merged_big = next(x for x in result if len(x["merged_from"]) == 4)
        merged_student = next(x for x in result if len(x["merged_from"]) == 2)

        assert set(merged_big["merged_from"]) == {
            "node_nguyen_van_an_doc001",
            "node_dr_nguyen_van_an_doc002",
            "node_nv_an_doc003",
            "node_nguyen_van_an_staff_doc006"
        }
        assert set(merged_big["labels"]) == {
            "PERSON", "LECTURER", "RESEARCHER", "STAFF"
        }

        assert set(merged_student["merged_from"]) == {
            "node_nguyen_van_an_student_doc004",
            "node_nguyen_van_an_undergrad_doc005"
        }
        assert set(merged_student["labels"]) == {
            "PERSON", "STUDENT"
        }

        all_merged_from = []
        for entity in result:
            all_merged_from.extend(entity["merged_from"])

        assert set(all_merged_from) == {
            "node_nguyen_van_an_doc001",
            "node_dr_nguyen_van_an_doc002",
            "node_nv_an_doc003",
            "node_nguyen_van_an_student_doc004",
            "node_nguyen_van_an_undergrad_doc005",
            "node_nguyen_van_an_staff_doc006",
            "node_nguyen_van_an_accent_doc007",
            "node_tran_thi_binh_doc008",
        }