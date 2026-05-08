from services.entity_resolution.preprocessing.normalize import build_embedding_text


def test_build_embedding_text_uses_name_only_and_ignores_aliases():
    text = build_embedding_text(
        ["FACULTY"],
        {
            "name": "Khoa Công nghệ Thông tin",
            "aliases": ["FIT", "Faculty of Information Technology", "Khoa CNTT"],
        },
    )

    assert text == "Khoa Công nghệ Thông tin"


def test_build_embedding_text_keeps_person_name_normalization_without_aliases():
    text = build_embedding_text(
        ["PERSON"],
        {
            "name": "GS.TS Chử Đức Trình",
            "aliases": ["Hiệu trưởng Trường ĐHCN", "Chu Duc Trinh"],
        },
    )

    assert text == "Chử Đức Trình"
