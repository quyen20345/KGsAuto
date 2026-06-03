"""Utilities for building deterministic canonical entity IDs."""

import re
import unicodedata

from apps.pipeline_api.core.entity_resolution.preprocessing.normalize import strip_accents


def build_canonical_id(canonical_name: str) -> str:
    """
    Generate deterministic canonical ID from canonical name.

    Format: node_[sanitized_name]
    - Remove Vietnamese diacritics
    - Lowercase
    - Replace spaces with underscores
    - Remove unsafe characters (keep only alphanumeric, underscore, hyphen)
    - Truncate to reasonable length (200 chars) to avoid extremely long IDs

    Args:
        canonical_name: The canonical name to generate ID from

    Returns:
        Canonical ID in format "node_[sanitized_name]"

    Examples:
        >>> build_canonical_id("Xuân Thủy")
        'node_xuan_thuy'
        >>> build_canonical_id("144 Xuân Thủy, Cầu Giấy, Hà Nội")
        'node_144_xuan_thuy_cau_giay_ha_noi'
    """
    if not canonical_name:
        return "node_unknown"

    # Normalize Unicode
    text = unicodedata.normalize("NFKC", canonical_name)

    # Remove diacritics
    text = strip_accents(text)

    # Lowercase
    text = text.lower()

    # Replace spaces with underscores
    text = text.replace(" ", "_")

    # Remove unsafe characters (keep only alphanumeric, underscore, hyphen)
    text = re.sub(r'[^a-z0-9_-]+', '_', text)

    # Collapse multiple underscores
    text = re.sub(r'_+', '_', text)

    # Strip leading/trailing underscores
    text = text.strip('_')

    # Handle empty result after sanitization
    if not text:
        return "node_unknown"

    # Truncate to reasonable length
    if len(text) > 200:
        text = text[:200].rstrip('_')

    # Prefix with node_
    return f"node_{text}"


def ensure_unique_canonical_id(base_id: str, existing_ids: set[str]) -> str:
    """
    Ensure canonical ID is unique by appending _2, _3, etc. if needed.

    Args:
        base_id: The base canonical ID
        existing_ids: Set of already used IDs

    Returns:
        Unique canonical ID

    Examples:
        >>> existing = {"node_test"}
        >>> ensure_unique_canonical_id("node_test", existing)
        'node_test_2'
        >>> existing.add("node_test_2")
        >>> ensure_unique_canonical_id("node_test", existing)
        'node_test_3'
    """
    if base_id not in existing_ids:
        return base_id

    # Try appending _2, _3, etc.
    counter = 2
    while True:
        candidate = f"{base_id}_{counter}"
        if candidate not in existing_ids:
            return candidate
        counter += 1
