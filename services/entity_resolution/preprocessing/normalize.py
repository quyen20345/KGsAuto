from __future__ import annotations

import re
import unicodedata
from typing import Any


STOP_KEYS = {
    "chunk_id",
    "model_extracted",
}


def normalize_text(value: Any) -> str:
    text = str(value or "")
    text = unicodedata.normalize("NFKC", text)
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def normalize_aliases(raw_aliases: Any) -> list[str]:
    if raw_aliases is None:
        return []
    if isinstance(raw_aliases, str):
        aliases = [raw_aliases]
    elif isinstance(raw_aliases, list):
        aliases = raw_aliases
    else:
        aliases = [str(raw_aliases)]

    out: list[str] = []
    seen: set[str] = set()
    for alias in aliases:
        alias_text = normalize_text(alias)
        if not alias_text:
            continue
        key = alias_text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(alias_text)
    return out


def normalize_properties(properties: dict[str, Any]) -> dict[str, Any]:
    props = dict(properties)
    props["name"] = normalize_text(props.get("name", ""))
    props["aliases"] = normalize_aliases(props.get("aliases"))

    evidence = props.get("description", "")
    props["description"] = normalize_text(evidence)

    return props


def primary_type(labels: list[str]) -> str:
    upper = [x.upper() for x in labels]
    if "PERSON" in upper:
        return "PERSON"
    if "ORGANIZATION" in upper:
        return "ORGANIZATION"
    if upper:
        return upper[0]
    return "UNKNOWN"


def normalize_person_name(name: str) -> str:
    """
    Normalize PERSON name by removing academic titles.

    Examples:
        "GS.TS Nguyễn Văn A" → "Nguyễn Văn A"
        "PGS.TS. Nguyễn Văn A" → "Nguyễn Văn A"
        "TS. Nguyễn Văn A" → "Nguyễn Văn A"

    Args:
        name: Full name with potential academic title

    Returns:
        Name without academic title
    """
    # Common Vietnamese academic titles
    titles = [
        r'GS\.TSKH\.?',    # Giáo sư Tiến sĩ Khoa học
        r'GS\.TS\.?',      # Giáo sư Tiến sĩ
        r'PGS\.TS\.?',     # Phó Giáo sư Tiến sĩ
        r'TS\.?',          # Tiến sĩ
        r'ThS\.?',         # Thạc sĩ
        r'CN\.?',          # Cử nhân
        r'KS\.?',          # Kỹ sư
    ]

    # Build pattern to match any title at start of name
    pattern = r'^(' + '|'.join(titles) + r')\s+'
    normalized = re.sub(pattern, '', name, flags=re.IGNORECASE)
    return normalized.strip()


def normalize_name_by_type(name: str, entity_type: str) -> str:
    """
    Normalize name based on entity type.

    Args:
        name: Entity name
        entity_type: Entity type (PERSON, ORGANIZATIONAL_UNIT, etc.)

    Returns:
        Normalized name
    """
    if entity_type == "PERSON":
        return normalize_person_name(name)

    # Add more type-specific normalizations here if needed
    # elif entity_type == "ORGANIZATIONAL_UNIT":
    #     return normalize_org_name(name)
    # elif entity_type == "ROLE":
    #     return normalize_role_name(name)

    return name


def normalize_aliases_by_type(aliases: list[str], entity_type: str) -> list[str]:
    """
    Normalize aliases based on entity type.

    Args:
        aliases: List of alias strings
        entity_type: Entity type (PERSON, ORGANIZATIONAL_UNIT, etc.)

    Returns:
        List of normalized aliases
    """
    if entity_type == "PERSON":
        # Normalize academic titles in aliases
        return [normalize_person_name(alias) for alias in aliases]

    # No normalization for other types
    return aliases


def build_embedding_text(labels: list[str], properties: dict[str, Any]) -> str:
    """
    Build embedding text from entity labels and properties.

    Format: name only.

    Args:
        labels: Entity labels (e.g., ["PERSON"])
        properties: Entity properties dict

    Returns:
        Formatted embedding text
    """
    name = normalize_text(properties.get("name", ""))
    ptype = primary_type(labels)
    return normalize_name_by_type(name, ptype)
