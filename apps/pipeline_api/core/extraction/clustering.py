"""Filename-based clustering helpers for extraction."""

import re
from pathlib import Path


_SPLIT_RE = re.compile(r"[^a-z0-9]+")
_DIGIT_TOKEN_RE = re.compile(r"^\d+$")


def tokenize_filename(file_path: Path) -> set[str]:
    stem = file_path.stem.lower()
    raw_tokens = _SPLIT_RE.split(stem)
    tokens = set()

    for token in raw_tokens:
        if not token or _DIGIT_TOKEN_RE.match(token):
            continue
        tokens.add(token)

    return tokens


def jaccard_similarity(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def cluster_markdown_files(files: list[Path], threshold: float) -> list[list[Path]]:
    token_map = {file_path: tokenize_filename(file_path) for file_path in files}
    sorted_files = sorted(files, key=lambda path: path.name)
    clusters: list[list[Path]] = []
    cluster_tokens: list[set[str]] = []

    for file_path in sorted_files:
        file_tokens = token_map[file_path]
        best_index = None
        best_score = -1.0

        for index, tokens in enumerate(cluster_tokens):
            score = jaccard_similarity(file_tokens, tokens)
            if score >= threshold and score > best_score:
                best_index = index
                best_score = score

        if best_index is None:
            clusters.append([file_path])
            cluster_tokens.append(set(file_tokens))
            continue

        clusters[best_index].append(file_path)
        cluster_tokens[best_index].update(file_tokens)

    return [sorted(cluster, key=lambda path: path.name) for cluster in clusters]
