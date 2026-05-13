"""Remove crawler metadata wrappers from Markdown files.

This script cleans already-crawled Markdown documents without crawling again.
It removes the crawler-specific `## Metadata` block and unwraps `## Content`,
leaving a plain Markdown document such as:

    # Title

    Real content...

By default it writes cleaned files to a separate output directory. Use
`--in-place --backup` to rewrite source files while keeping `.bak` copies.
"""

from __future__ import annotations

import argparse
import re
import shutil
from dataclasses import dataclass
from pathlib import Path


METADATA_HEADING_RE = re.compile(r"^##\s+Metadata\s*$", re.IGNORECASE | re.MULTILINE)
CONTENT_HEADING_RE = re.compile(r"^##\s+Content\s*$", re.IGNORECASE | re.MULTILINE)
NEXT_H2_RE = re.compile(r"^##\s+.+$", re.MULTILINE)
H1_RE = re.compile(r"^#\s+.+$", re.MULTILINE)

# Metadata shape written by services/crawler/main.py before `## Content`.
LEGACY_FRONT_MATTER_LINE_RE = re.compile(
    r"^\s*-\s+(?:ID|Date|URL|Categories|Tags)\s*:\s*.*$",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass(frozen=True)
class CleanResult:
    text: str
    removed_metadata_block: bool
    removed_content_heading: bool
    removed_legacy_lines: int
    changed: bool


def clean_markdown(raw_text: str) -> CleanResult:
    """Return Markdown with crawler metadata removed.

    Supported input forms:
    1. `# title` + `## Metadata` + metadata lines + `## Content` + body
    2. `# title` + legacy `- URL:`/`- ID:` lines + `## Content` + body
    3. already-clean Markdown (returned mostly unchanged, normalized lightly)
    """

    original = raw_text
    text = raw_text.replace("\xa0", " ").replace("\r\n", "\n").replace("\r", "\n")

    removed_metadata_block = False
    metadata_match = METADATA_HEADING_RE.search(text)
    if metadata_match:
        next_section = NEXT_H2_RE.search(text, metadata_match.end())
        end = next_section.start() if next_section else len(text)
        text = text[: metadata_match.start()] + text[end:]
        removed_metadata_block = True

    removed_legacy_lines = 0
    first_content = CONTENT_HEADING_RE.search(text)
    if first_content:
        before_content = text[: first_content.start()]
        after_content = text[first_content.start() :]
        cleaned_before, removed_legacy_lines = LEGACY_FRONT_MATTER_LINE_RE.subn("", before_content)
        text = cleaned_before + after_content

    removed_content_heading = False
    content_match = CONTENT_HEADING_RE.search(text)
    if content_match:
        before_content = text[: content_match.start()].strip()
        body = text[content_match.end() :].strip()
        if before_content:
            text = f"{before_content}\n\n{body}"
        else:
            text = body
        removed_content_heading = True

    text = _normalize_spacing(text)
    return CleanResult(
        text=text,
        removed_metadata_block=removed_metadata_block,
        removed_content_heading=removed_content_heading,
        removed_legacy_lines=removed_legacy_lines,
        changed=text != _normalize_spacing(original),
    )


def clean_directory(
    input_dir: Path,
    output_dir: Path | None,
    in_place: bool,
    backup: bool,
    dry_run: bool,
) -> dict[str, int]:
    if not input_dir.exists() or not input_dir.is_dir():
        raise ValueError(f"Input directory does not exist or is not a directory: {input_dir}")
    if in_place and output_dir is not None:
        raise ValueError("Use either --in-place or --output-dir, not both")
    if not in_place and output_dir is None:
        raise ValueError("Provide --output-dir, or use --in-place")

    markdown_files = sorted(input_dir.rglob("*.md"))
    stats = {
        "files_seen": len(markdown_files),
        "files_changed": 0,
        "metadata_blocks_removed": 0,
        "content_headings_removed": 0,
        "legacy_metadata_lines_removed": 0,
        "files_written": 0,
        "backups_written": 0,
    }

    if output_dir is not None and not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    for source in markdown_files:
        raw_text = source.read_text(encoding="utf-8", errors="ignore")
        result = clean_markdown(raw_text)

        if result.changed:
            stats["files_changed"] += 1
        if result.removed_metadata_block:
            stats["metadata_blocks_removed"] += 1
        if result.removed_content_heading:
            stats["content_headings_removed"] += 1
        stats["legacy_metadata_lines_removed"] += result.removed_legacy_lines

        if dry_run:
            continue

        if in_place:
            destination = source
            if backup and result.changed:
                backup_path = source.with_suffix(source.suffix + ".bak")
                shutil.copy2(source, backup_path)
                stats["backups_written"] += 1
        else:
            assert output_dir is not None
            destination = output_dir / source.relative_to(input_dir)
            destination.parent.mkdir(parents=True, exist_ok=True)

        if in_place and not result.changed:
            continue
        destination.write_text(result.text, encoding="utf-8")
        stats["files_written"] += 1

    return stats


def _normalize_spacing(text: str) -> str:
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text + "\n" if text else ""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Remove crawler metadata from Markdown files")
    parser.add_argument("--input-dir", type=Path, default=Path("data/raw/uet"))
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--in-place", action="store_true", help="Rewrite input files instead of writing to --output-dir")
    parser.add_argument("--backup", action="store_true", help="With --in-place, keep .bak copies of changed files")
    parser.add_argument("--dry-run", action="store_true", help="Print stats without writing files")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    stats = clean_directory(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        in_place=args.in_place,
        backup=args.backup,
        dry_run=args.dry_run,
    )
    for key, value in stats.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
