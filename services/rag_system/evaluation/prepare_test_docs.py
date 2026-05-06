"""Prepare clean, ontology-balanced Markdown documents for Ragas testset generation.

This script is intentionally separate from the runtime RAG pipeline. It removes
source metadata from Markdown content before Ragas builds embeddings and document
similarity graphs, then selects a representative subset using the extraction
ontology as a guide.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.extraction.prompt import ENTITY_LABELS


DEFAULT_INPUT_DIR = Path("data/raw/uet")
DEFAULT_OUTPUT_DIR = Path("data/evaluation/ragas/clean_docs")
DEFAULT_MANIFEST_PATH = Path("data/evaluation/ragas/clean_manifest.csv")
DEFAULT_SUMMARY_PATH = Path("data/evaluation/ragas/clean_summary.json")
DEFAULT_TARGET_COUNT = 100
DEFAULT_MIN_CONTENT_CHARS = 500
DEFAULT_MAX_CONTENT_CHARS = 7000

METADATA_SECTION_RE = re.compile(r"^##\s+Metadata\s*$", re.IGNORECASE | re.MULTILINE)
CONTENT_SECTION_RE = re.compile(r"^##\s+Content\s*$", re.IGNORECASE | re.MULTILINE)
H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
NEXT_H2_RE = re.compile(r"^##\s+.+$", re.MULTILINE)

METADATA_LEAK_MARKERS = (
    "## metadata",
    "**url**",
    "**slug**",
    "**published**",
    "**modified**",
    "**type**",
    "**status**",
    "**author id**",
)

RELATIONSHIP_KEYWORDS = (
    "truc thuoc",
    "thuoc",
    "quan ly",
    "dao tao",
    "to chuc",
    "cung cap",
    "hop tac",
    "dia chi",
    "email",
    "phu trach",
    "tham muu",
    "giup viec",
    "lien he",
    "quan he",
    "ky ket",
)

STRUCTURE_KEYWORDS = (
    "chuc nang",
    "nhiem vu",
    "to chuc nhan su",
    "to chuc bo may",
    "ban chu nhiem",
    "danh sach",
    "chuong trinh dao tao",
    "dia chi lien he",
)

TEMPORAL_NOISE_KEYWORDS = (
    "lich thi",
    "ket qua",
    "trieu tap",
    "du kien",
    "hoan tra",
    "bao ve luan an",
    "nghi hoc",
    "dieu chinh",
    "cap nhat danh sach",
    "nop ho so",
    "moi tham du",
    "dau gia",
    "canh bao",
    "tet",
)

LABEL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "UNIVERSITY": ("truong dai hoc", "dai hoc quoc gia", "dhqghn", "dhcn"),
    "FACULTY": ("khoa ", "faculty"),
    "DEPARTMENT": ("bo mon", "department"),
    "INSTITUTE": ("vien ", "institute"),
    "LAB": ("phong thi nghiem", "laboratory", " lab"),
    "ADMINISTRATIVE_UNIT": ("phong ", "ban ", "hoi dong", "trung tam", "van phong"),
    "PROGRAM": ("chuong trinh dao tao", "nganh ", "cu nhan", "ky su", "thac si", "tien si"),
    "COURSE": ("hoc phan", "mon hoc", "lop hoc", "course"),
    "PERSON": ("gs", "pgs", "ts", "ths", "ho va ten", "email", "giang vien", "can bo"),
    "EVENT": ("hoi thao", "su kien", "seminar", "workshop", "ngay hoi", "hoi nghi", "tap huan"),
    "RESEARCH_PROJECT": ("de tai", "du an", "project"),
    "RESEARCH_AREA": ("linh vuc nghien cuu", "nghien cuu", "tri tue nhan tao", "cong nghe"),
    "PUBLICATION": ("bai bao", "tap chi", "luan an", "luan van", "bao cao", "publication"),
    "DOCUMENT": ("quy che", "quy dinh", "huong dan", "thong bao", "van ban", "ke hoach"),
    "SCHOLARSHIP": ("hoc bong", "grant", "financial support"),
    "PARTNERSHIP": ("hop tac", "doi tac", "ky ket", "thoa thuan", "mou", "lien ket"),
    "LOCATION": ("ha noi", "hoa lac", "xuan thuy", "cau giay", "location", "tp "),
    "BUILDING": ("nha ", "toa nha", "giang duong", "building"),
    "ROOM": ("phong ", "room"),
    "WEBSITE": ("website", "http", "portal", "cong thong tin"),
    "SYSTEM": ("he thong", "phan mem", "platform", "system"),
}


@dataclass(frozen=True)
class GroupRule:
    name: str
    quota: int
    labels: tuple[str, ...]
    keywords: tuple[str, ...]


GROUP_RULES: tuple[GroupRule, ...] = (
    GroupRule(
        name="organization_structure",
        quota=25,
        labels=("UNIVERSITY", "FACULTY", "DEPARTMENT", "INSTITUTE", "LAB", "ADMINISTRATIVE_UNIT"),
        keywords=(
            "co cau to chuc",
            "khoa ",
            "vien ",
            "phong ",
            "ban giam hieu",
            "hoi dong",
            "trung tam",
            "bo mon",
            "phong thi nghiem",
            "don vi truc thuoc",
            "chuc nang",
            "nhiem vu",
        ),
    ),
    GroupRule(
        name="education_program",
        quota=15,
        labels=("PROGRAM", "COURSE", "FACULTY", "DEPARTMENT"),
        keywords=(
            "dao tao",
            "chuong trinh dao tao",
            "nganh ",
            "hoc phan",
            "khoa hoc",
            "cu nhan",
            "ky su",
            "thac si",
            "tien si",
            "tuyen sinh",
            "chuan dau ra",
        ),
    ),
    GroupRule(
        name="people_roles",
        quota=15,
        labels=("PERSON", "FACULTY", "INSTITUTE", "ADMINISTRATIVE_UNIT"),
        keywords=(
            "ho va ten",
            "chuc vu",
            "truong phong",
            "pho truong phong",
            "chu nhiem",
            "pho chu nhiem",
            "vien truong",
            "hieu truong",
            "email",
            "giang vien",
            "can bo",
            "nhan su",
            "danh sach",
        ),
    ),
    GroupRule(
        name="document_policy",
        quota=12,
        labels=("DOCUMENT", "SYSTEM", "WEBSITE"),
        keywords=(
            "quy che",
            "quy dinh",
            "huong dan",
            "thong bao",
            "mau don",
            "van ban",
            "ke hoach",
            "cong van",
            "he thong",
            "website",
            "portal",
            "cong thong tin",
            "chinh sach",
        ),
    ),
    GroupRule(
        name="student_support",
        quota=10,
        labels=("SCHOLARSHIP", "DOCUMENT", "ADMINISTRATIVE_UNIT"),
        keywords=(
            "sinh vien",
            "nguoi hoc",
            "hoc bong",
            "mien giam hoc phi",
            "tro cap",
            "bao hiem y te",
            "ren luyen",
            "viec lam",
            "cong tac sinh vien",
            "nhap hoc",
            "ky tuc xa",
        ),
    ),
    GroupRule(
        name="research",
        quota=10,
        labels=("RESEARCH_PROJECT", "RESEARCH_AREA", "PUBLICATION", "LAB"),
        keywords=(
            "nghien cuu",
            "de tai",
            "du an",
            "cong bo",
            "bai bao",
            "tap chi",
            "hoi thao khoa hoc",
            "luan an",
            "luan van",
            "phong thi nghiem",
            "linh vuc nghien cuu",
            "sang che",
        ),
    ),
    GroupRule(
        name="partnership",
        quota=6,
        labels=("PARTNERSHIP", "UNIVERSITY", "INSTITUTE", "LOCATION"),
        keywords=(
            "hop tac",
            "doi tac",
            "ky ket",
            "thoa thuan",
            "mou",
            "doanh nghiep",
            "quoc te",
            "trong nuoc",
            "lien ket",
            "trao doi",
        ),
    ),
    GroupRule(
        name="location_facility",
        quota=4,
        labels=("LOCATION", "BUILDING", "ROOM", "LAB"),
        keywords=(
            "dia chi",
            "nha ",
            "phong ",
            "co so",
            "campus",
            "hoa lac",
            "xuan thuy",
            "cau giay",
            "ha noi",
            "toa nha",
            "tang ",
        ),
    ),
    GroupRule(
        name="event_news",
        quota=3,
        labels=("EVENT", "PERSON"),
        keywords=("hoi thao", "su kien", "le ", "ngay hoi", "seminar", "workshop", "hoi nghi", "tap huan", "trien lam", "cuoc thi"),
    ),
)


@dataclass
class ParsedMarkdown:
    title: str
    content: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class DocumentCandidate:
    source_path: Path
    title: str
    clean_text: str
    word_count: int
    matched_labels: list[str]
    group_scores: dict[str, int]
    primary_group: str
    score: float
    fingerprint: str
    source_part: int
    source_part_count: int
    char_count: int
    accepted: bool = False
    output_path: Path | None = None
    reject_reason: str | None = None

    @property
    def selectable(self) -> bool:
        return self.reject_reason is None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare clean Markdown docs for Ragas testset generation.")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY_PATH)
    parser.add_argument("--target-count", type=int, default=DEFAULT_TARGET_COUNT)
    parser.add_argument("--min-content-chars", type=int, default=DEFAULT_MIN_CONTENT_CHARS)
    parser.add_argument(
        "--max-content-chars",
        type=int,
        default=DEFAULT_MAX_CONTENT_CHARS,
        help="Maximum characters per generated clean Markdown file, including title.",
    )
    parser.add_argument("--max-per-group", type=int, default=0, help="Optional hard cap per selected group.")
    parser.add_argument("--dry-run", action="store_true", help="Compute selection and print summary without writing files.")
    return parser.parse_args()


def parse_markdown_document(raw_text: str, fallback_title: str) -> ParsedMarkdown:
    title = _extract_title(raw_text) or fallback_title
    metadata = _extract_metadata(raw_text)
    content = _extract_content(raw_text)
    content = _normalize_content(content)
    return ParsedMarkdown(title=title, content=content, metadata=metadata)


def prepare_documents(
    input_dir: Path = DEFAULT_INPUT_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    summary_path: Path = DEFAULT_SUMMARY_PATH,
    target_count: int = DEFAULT_TARGET_COUNT,
    min_content_chars: int = DEFAULT_MIN_CONTENT_CHARS,
    max_content_chars: int = DEFAULT_MAX_CONTENT_CHARS,
    max_per_group: int = 0,
    dry_run: bool = False,
) -> dict[str, Any]:
    if target_count <= 0:
        raise ValueError("target_count must be positive")
    if min_content_chars < 0:
        raise ValueError("min_content_chars must be non-negative")
    if max_content_chars <= 0:
        raise ValueError("max_content_chars must be positive")
    if max_content_chars <= min_content_chars:
        raise ValueError("max_content_chars must be greater than min_content_chars")

    _validate_group_labels()
    markdown_files = sorted(input_dir.rglob("*.md"))
    quotas = make_group_quotas(target_count)
    candidates = []
    for path in markdown_files:
        candidates.extend(
            build_candidates(
                path,
                min_content_chars=min_content_chars,
                max_content_chars=max_content_chars,
            )
        )
    select_candidates(candidates, quotas=quotas, target_count=target_count, max_per_group=max_per_group)
    assign_output_paths(candidates, output_dir)

    summary = build_summary(
        candidates,
        input_dir=input_dir,
        output_dir=output_dir,
        manifest_path=manifest_path,
        summary_path=summary_path,
        target_count=target_count,
        min_content_chars=min_content_chars,
        max_content_chars=max_content_chars,
        source_file_count=len(markdown_files),
        quotas=quotas,
    )

    if not dry_run:
        write_outputs(
            candidates,
            output_dir=output_dir,
            manifest_path=manifest_path,
            summary_path=summary_path,
            summary=summary,
            max_content_chars=max_content_chars,
        )

    return summary


def build_candidate(
    path: Path,
    min_content_chars: int,
    max_content_chars: int = DEFAULT_MAX_CONTENT_CHARS,
) -> DocumentCandidate:
    return build_candidates(path, min_content_chars=min_content_chars, max_content_chars=max_content_chars)[0]


def build_candidates(path: Path, min_content_chars: int, max_content_chars: int) -> list[DocumentCandidate]:
    try:
        raw_text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raw_text = path.read_text(encoding="utf-8", errors="ignore")

    parsed = parse_markdown_document(raw_text, fallback_title=path.stem)
    clean_body = parsed.content.strip()
    body_budget = max_content_chars - len(f"# {parsed.title} - Phần 999\n\n\n")
    if body_budget <= 0:
        body_budget = max_content_chars
    content_parts = split_content(clean_body, max_chars=body_budget)

    return [
        _build_candidate_from_part(
            path=path,
            title=parsed.title,
            clean_body=part,
            source_part=index,
            source_part_count=len(content_parts),
            min_content_chars=min_content_chars,
            max_content_chars=max_content_chars,
        )
        for index, part in enumerate(content_parts, start=1)
    ]


def _build_candidate_from_part(
    path: Path,
    title: str,
    clean_body: str,
    source_part: int,
    source_part_count: int,
    min_content_chars: int,
    max_content_chars: int,
) -> DocumentCandidate:
    clean_body = clean_body.strip()
    candidate_title = title if source_part_count == 1 else f"{title} - Phần {source_part}"
    clean_text = f"# {candidate_title}\n\n{clean_body}\n" if clean_body else f"# {candidate_title}\n"
    normalized_text = normalize_for_match(f"{candidate_title}\n{clean_body}")
    matched_labels = match_entity_labels(normalized_text)
    group_scores = score_groups(normalized_text, matched_labels)
    primary_group = max(group_scores, key=group_scores.get) if group_scores else "unknown"
    if group_scores.get(primary_group, 0) <= 0:
        primary_group = "unknown"
    word_count = count_words(clean_body)
    score = score_document(candidate_title, clean_body, normalized_text, matched_labels, group_scores)
    reject_reason = initial_reject_reason(
        clean_body=clean_body,
        normalized_text=normalized_text,
        matched_labels=matched_labels,
        primary_group=primary_group,
        min_content_chars=min_content_chars,
    )
    if reject_reason is None and len(clean_text) > max_content_chars:
        reject_reason = "too_long_after_split"

    return DocumentCandidate(
        source_path=path,
        title=candidate_title,
        clean_text=clean_text,
        word_count=word_count,
        matched_labels=matched_labels,
        group_scores=group_scores,
        primary_group=primary_group,
        score=score,
        fingerprint=fingerprint_text(clean_body),
        source_part=source_part,
        source_part_count=source_part_count,
        char_count=len(clean_text),
        reject_reason=reject_reason,
    )


def select_candidates(
    candidates: list[DocumentCandidate],
    quotas: dict[str, int],
    target_count: int,
    max_per_group: int = 0,
) -> None:
    accepted: list[DocumentCandidate] = []
    fingerprints: set[str] = set()
    group_counts: Counter[str] = Counter()

    def try_accept(candidate: DocumentCandidate) -> bool:
        if len(accepted) >= target_count:
            return False
        if not candidate.selectable or candidate.accepted:
            return False
        if candidate.fingerprint in fingerprints:
            candidate.reject_reason = "duplicate_selected"
            return False
        if max_per_group and group_counts[candidate.primary_group] >= max_per_group:
            return False

        candidate.accepted = True
        candidate.reject_reason = None
        accepted.append(candidate)
        fingerprints.add(candidate.fingerprint)
        group_counts[candidate.primary_group] += 1
        return True

    for group_name, quota in quotas.items():
        group_candidates = sorted(
            (candidate for candidate in candidates if candidate.primary_group == group_name),
            key=_selection_sort_key,
        )
        for candidate in group_candidates:
            if group_counts[group_name] >= quota:
                break
            try_accept(candidate)

    fill_pool = sorted(candidates, key=_selection_sort_key)
    for candidate in fill_pool:
        if len(accepted) >= target_count:
            break
        try_accept(candidate)

    for candidate in candidates:
        if candidate.reject_reason is None and not candidate.accepted:
            candidate.reject_reason = "not_selected"


def assign_output_paths(candidates: list[DocumentCandidate], output_dir: Path) -> None:
    used_names: set[str] = set()
    accepted = sorted((candidate for candidate in candidates if candidate.accepted), key=lambda item: str(item.source_path))
    for index, candidate in enumerate(accepted, start=1):
        output_name = make_output_name(index, candidate_output_source_name(candidate), used_names)
        candidate.output_path = output_dir / output_name


def write_outputs(
    candidates: list[DocumentCandidate],
    output_dir: Path,
    manifest_path: Path,
    summary_path: Path,
    summary: dict[str, Any],
    max_content_chars: int,
) -> None:
    too_long = [candidate for candidate in candidates if candidate.accepted and candidate.char_count > max_content_chars]
    if too_long:
        examples = ", ".join(candidate.title for candidate in too_long[:3])
        raise RuntimeError(f"Accepted clean docs exceed max_content_chars={max_content_chars}: {examples}")

    output_dir.mkdir(parents=True, exist_ok=True)
    for existing_md in output_dir.glob("*.md"):
        existing_md.unlink()

    for candidate in candidates:
        if candidate.accepted and candidate.output_path:
            candidate.output_path.write_text(candidate.clean_text, encoding="utf-8")

    write_manifest(candidates, manifest_path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_manifest(candidates: list[DocumentCandidate], manifest_path: Path) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "source_path",
        "output_path",
        "title",
        "accepted",
        "source_part",
        "source_part_count",
        "primary_group",
        "score",
        "char_count",
        "word_count",
        "matched_labels",
        "reject_reason",
    ]
    with manifest_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for candidate in sorted(candidates, key=lambda item: str(item.source_path)):
            writer.writerow(
                {
                    "source_path": str(candidate.source_path),
                    "output_path": str(candidate.output_path) if candidate.output_path else "",
                    "title": candidate.title,
                    "accepted": candidate.accepted,
                    "source_part": candidate.source_part,
                    "source_part_count": candidate.source_part_count,
                    "primary_group": candidate.primary_group,
                    "score": f"{candidate.score:.2f}",
                    "char_count": candidate.char_count,
                    "word_count": candidate.word_count,
                    "matched_labels": ";".join(candidate.matched_labels),
                    "reject_reason": candidate.reject_reason or "",
                }
            )


def build_summary(
    candidates: list[DocumentCandidate],
    input_dir: Path,
    output_dir: Path,
    manifest_path: Path,
    summary_path: Path,
    target_count: int,
    min_content_chars: int,
    max_content_chars: int,
    source_file_count: int,
    quotas: dict[str, int],
) -> dict[str, Any]:
    accepted = [candidate for candidate in candidates if candidate.accepted]
    reject_reasons = Counter(candidate.reject_reason or "accepted" for candidate in candidates if not candidate.accepted)
    candidate_metadata_leak_count = sum(1 for candidate in candidates if has_metadata_leak(candidate.clean_text))
    metadata_leak_count = sum(1 for candidate in accepted if has_metadata_leak(candidate.clean_text))
    split_source_files = len({candidate.source_path for candidate in candidates if candidate.source_part_count > 1})
    split_candidate_docs = sum(1 for candidate in candidates if candidate.source_part_count > 1)
    groups: dict[str, dict[str, int]] = {}
    for group in quotas:
        groups[group] = {
            "quota": quotas[group],
            "accepted": sum(1 for candidate in accepted if candidate.primary_group == group),
            "candidates": sum(1 for candidate in candidates if candidate.primary_group == group and candidate.selectable),
        }

    return {
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "manifest": str(manifest_path),
        "summary": str(summary_path),
        "target_count": target_count,
        "input_files": source_file_count,
        "candidate_docs": len(candidates),
        "accepted_files": len(accepted),
        "rejected_files": len(candidates) - len(accepted),
        "min_content_chars": min_content_chars,
        "max_content_chars": max_content_chars,
        "split_source_files": split_source_files,
        "split_candidate_docs": split_candidate_docs,
        "max_accepted_chars": max((candidate.char_count for candidate in accepted), default=0),
        "groups": groups,
        "reject_reasons": dict(sorted(reject_reasons.items())),
        "metadata_leak_count": metadata_leak_count,
        "candidate_metadata_leak_count": candidate_metadata_leak_count,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def make_group_quotas(target_count: int) -> dict[str, int]:
    base_total = sum(rule.quota for rule in GROUP_RULES)
    scaled: list[tuple[str, int, float]] = []
    for rule in GROUP_RULES:
        raw = target_count * rule.quota / base_total
        floor_value = int(raw)
        scaled.append((rule.name, floor_value, raw - floor_value))

    remaining = target_count - sum(item[1] for item in scaled)
    order = sorted(range(len(scaled)), key=lambda index: scaled[index][2], reverse=True)
    quota_values = {name: value for name, value, _ in scaled}
    for index in order[:remaining]:
        name = scaled[index][0]
        quota_values[name] += 1
    return quota_values


def score_groups(normalized_text: str, matched_labels: list[str]) -> dict[str, int]:
    matched_label_set = set(matched_labels)
    scores = {}
    for rule in GROUP_RULES:
        label_hits = len(matched_label_set & set(rule.labels))
        keyword_hits = count_keyword_hits(normalized_text, rule.keywords)
        scores[rule.name] = label_hits * 4 + keyword_hits * 5
    return scores


def score_document(
    title: str,
    clean_body: str,
    normalized_text: str,
    matched_labels: list[str],
    group_scores: dict[str, int],
) -> float:
    word_count = count_words(clean_body)
    length_score = min(word_count / 20, 20)
    label_score = len(matched_labels) * 8
    group_score = max(group_scores.values()) if group_scores else 0
    relationship_score = min(count_keyword_hits(normalized_text, RELATIONSHIP_KEYWORDS), 10) * 3
    structure_score = min(count_keyword_hits(normalized_text, STRUCTURE_KEYWORDS), 8) * 3
    table_score = 5 if "|" in clean_body and "---" in clean_body else 0
    contact_score = 5 if re.search(r"[\w.+-]+@[\w.-]+", clean_body) or "dien thoai" in normalized_text else 0
    title_score = 5 if title and title.strip() else 0
    noise_penalty = min(count_keyword_hits(normalize_for_match(title), TEMPORAL_NOISE_KEYWORDS) * 12, 36)
    noise_penalty += min(count_keyword_hits(normalized_text, TEMPORAL_NOISE_KEYWORDS), 8) * 2
    return label_score + group_score + relationship_score + structure_score + length_score + table_score + contact_score + title_score - noise_penalty


def initial_reject_reason(
    clean_body: str,
    normalized_text: str,
    matched_labels: list[str],
    primary_group: str,
    min_content_chars: int,
) -> str | None:
    if len(clean_body.strip()) < min_content_chars:
        return "too_short"
    if has_metadata_leak(clean_body):
        return "metadata_leftover"
    if primary_group == "unknown" or not matched_labels:
        return "no_ontology_match"
    if count_words(clean_body) < 30:
        return "heading_only"
    if not normalized_text.strip():
        return "empty_content"
    return None


def match_entity_labels(normalized_text: str) -> list[str]:
    return [label for label, keywords in LABEL_KEYWORDS.items() if count_keyword_hits(normalized_text, keywords) > 0]


def normalize_for_match(text: str) -> str:
    text = text.replace("\u0111", "d").replace("\u0110", "D")
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.lower().replace("_", " ")
    ascii_text = re.sub(r"[^a-z0-9@./:+-]+", " ", ascii_text)
    return re.sub(r"\s+", " ", ascii_text).strip()


def count_keyword_hits(normalized_text: str, keywords: tuple[str, ...]) -> int:
    padded = f" {normalized_text} "
    return sum(1 for keyword in keywords if keyword in padded)


def count_words(text: str) -> int:
    return len(re.findall(r"\w+", normalize_for_match(text)))


def split_content(content: str, max_chars: int) -> list[str]:
    content = content.strip()
    if not content:
        return [""]
    if len(content) <= max_chars:
        return [content]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for block in _split_blocks(content):
        block_len = len(block)
        separator_len = 2 if current else 0
        if block_len > max_chars:
            if current:
                chunks.append("\n\n".join(current).strip())
                current = []
                current_len = 0
            chunks.extend(_split_large_block(block, max_chars))
            continue

        if current and current_len + separator_len + block_len > max_chars:
            chunks.append("\n\n".join(current).strip())
            current = [block]
            current_len = block_len
        else:
            current.append(block)
            current_len += separator_len + block_len

    if current:
        chunks.append("\n\n".join(current).strip())

    return [chunk for chunk in chunks if chunk.strip()]


def _split_blocks(content: str) -> list[str]:
    blocks = [block.strip() for block in re.split(r"\n\s*\n", content) if block.strip()]
    return blocks or [content]


def _split_large_block(block: str, max_chars: int) -> list[str]:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if len(lines) > 1:
        return _pack_units(lines, max_chars=max_chars, separator="\n")
    return _pack_units(block.split(), max_chars=max_chars, separator=" ")


def _pack_units(units: list[str], max_chars: int, separator: str) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    separator_len = len(separator)

    for unit in units:
        if len(unit) > max_chars:
            if current:
                chunks.append(separator.join(current).strip())
                current = []
                current_len = 0
            chunks.extend(unit[i : i + max_chars] for i in range(0, len(unit), max_chars))
            continue

        extra = separator_len if current else 0
        if current and current_len + extra + len(unit) > max_chars:
            chunks.append(separator.join(current).strip())
            current = [unit]
            current_len = len(unit)
        else:
            current.append(unit)
            current_len += extra + len(unit)

    if current:
        chunks.append(separator.join(current).strip())
    return chunks


def has_metadata_leak(text: str) -> bool:
    lowered = text.lower()
    return bool(METADATA_SECTION_RE.search(text)) or any(marker in lowered for marker in METADATA_LEAK_MARKERS)


def fingerprint_text(text: str) -> str:
    normalized = normalize_for_match(text)[:1500]
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()


def make_output_name(index: int, source_name: str, used_names: set[str]) -> str:
    stem = Path(source_name).stem.strip() or "document"
    suffix = Path(source_name).suffix or ".md"
    base = f"{index:03d}_{stem}{suffix}"
    output_name = base
    counter = 2
    while output_name in used_names:
        output_name = f"{index:03d}_{stem}_{counter}{suffix}"
        counter += 1
    used_names.add(output_name)
    return output_name


def candidate_output_source_name(candidate: DocumentCandidate) -> str:
    if candidate.source_part_count == 1:
        return candidate.source_path.name
    suffix = candidate.source_path.suffix or ".md"
    return f"{candidate.source_path.stem}_part{candidate.source_part:03d}{suffix}"


def _extract_title(raw_text: str) -> str | None:
    match = H1_RE.search(raw_text)
    if not match:
        return None
    return match.group(1).strip()


def _extract_metadata(raw_text: str) -> dict[str, str]:
    metadata_match = METADATA_SECTION_RE.search(raw_text)
    if not metadata_match:
        return {}
    next_section = NEXT_H2_RE.search(raw_text, metadata_match.end())
    end = next_section.start() if next_section else len(raw_text)
    metadata_text = raw_text[metadata_match.end() : end]
    metadata: dict[str, str] = {}
    for line in metadata_text.splitlines():
        match = re.match(r"\s*-\s*\*\*(.+?)\*\*:\s*(.+?)\s*$", line)
        if match:
            key = normalize_for_match(match.group(1)).replace(" ", "_")
            metadata[key] = match.group(2).strip()
    return metadata


def _extract_content(raw_text: str) -> str:
    content_match = CONTENT_SECTION_RE.search(raw_text)
    if content_match:
        return raw_text[content_match.end() :]

    without_title = H1_RE.sub("", raw_text, count=1)
    metadata_match = METADATA_SECTION_RE.search(without_title)
    if metadata_match:
        next_section = NEXT_H2_RE.search(without_title, metadata_match.end())
        if next_section:
            without_title = without_title[: metadata_match.start()] + without_title[next_section.start() :]
        else:
            without_title = without_title[: metadata_match.start()]
    return without_title


def _normalize_content(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _selection_sort_key(candidate: DocumentCandidate) -> tuple[float, int, str]:
    return (-candidate.score, -candidate.word_count, str(candidate.source_path))


def _allowed_entity_labels() -> set[str]:
    return set(re.findall(r"-\s+([A-Z_]+):", ENTITY_LABELS))


def _validate_group_labels() -> None:
    allowed_labels = _allowed_entity_labels()
    referenced_labels = set(LABEL_KEYWORDS)
    for rule in GROUP_RULES:
        referenced_labels.update(rule.labels)
    unknown = sorted(referenced_labels - allowed_labels)
    if unknown:
        raise ValueError("Unknown entity labels referenced by test-doc selector: " + ", ".join(unknown))


def main() -> None:
    args = parse_args()
    summary = prepare_documents(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        manifest_path=args.manifest,
        summary_path=args.summary,
        target_count=args.target_count,
        min_content_chars=args.min_content_chars,
        max_content_chars=args.max_content_chars,
        max_per_group=args.max_per_group,
        dry_run=args.dry_run,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
