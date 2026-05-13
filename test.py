import json
from pathlib import Path
from typing import Any


PATH = Path("data/evaluation/testset150_graph_search.jsonl")
ROW_INDEX = 0
PREVIEW_CHARS = 4_000
FIELDS_TO_INSPECT = [
    "contexts",
    "retrieved_contexts",
    "retrieval_evidence",
    "derived_contexts",
    "reasoning_steps",
    "metadata",
]
MARKERS = [
    "initial_context",
    "text_summary",
    "kg_summary",
    "reasoning",
    "subqueries",
    "sub_queries",
    "expanded_queries",
    "Knowledge Graph Data",
    "Document Chunks",
    "Text Summary",
    "KG Summary",
]


def load_row(path: Path, row_index: int) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        for index, line in enumerate(file):
            if index == row_index:
                return json.loads(line)
    raise IndexError(f"Row index not found: {row_index}")


def to_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def value_size(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, (list, dict)):
        return len(value)
    return len(str(value))


def print_fields(row: dict[str, Any]) -> None:
    print("FIELDS")
    print("=" * 80)
    for key, value in row.items():
        print(f"- {key}: type={type(value).__name__}, size={value_size(value)}")


def print_marker_hits(field_name: str, text: str) -> None:
    hits = []
    for marker in MARKERS:
        position = text.find(marker)
        if position >= 0:
            hits.append((marker, position))

    if not hits:
        print(f"Marker hits in {field_name}: none")
        return

    print(f"Marker hits in {field_name}:")
    for marker, position in hits:
        print(f"  - {marker!r} at char {position:,}")


def preview_field(row: dict[str, Any], field_name: str) -> None:
    value = row.get(field_name)
    text = to_text(value)

    print("\n" + "=" * 80)
    print(field_name)
    print("=" * 80)
    print(f"Type: {type(value).__name__}")
    print(f"Size: {value_size(value)}")
    print(f"Serialized chars: {len(text):,}")
    print_marker_hits(field_name, text)
    print("-" * 80)
    print(text[:PREVIEW_CHARS])
    if len(text) > PREVIEW_CHARS:
        print("-" * 80)
        print(f"... truncated, remaining chars: {len(text) - PREVIEW_CHARS:,}")


def main() -> None:
    if not PATH.exists():
        raise FileNotFoundError(f"JSONL file not found: {PATH}")

    row = load_row(PATH, ROW_INDEX)
    print(f"File: {PATH}")
    print(f"Row index: {ROW_INDEX}")
    print_fields(row)

    for field_name in FIELDS_TO_INSPECT:
        preview_field(row, field_name)


if __name__ == "__main__":
    main()
