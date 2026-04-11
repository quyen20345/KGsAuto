from __future__ import annotations

from collections import defaultdict
from fuzzywuzzy import fuzz

from ..types import ClusterAssignment


def compute_name_similarity(name1: str, name2: str, entity_type: str = "PERSON") -> float:
    """
    Compute fuzzy name similarity for entities.
    Normalizes names (removes academic titles for PERSON) before comparison.

    Args:
        name1: First entity name
        name2: Second entity name
        entity_type: Entity type (PERSON, ORGANIZATIONAL_UNIT, etc.)

    Returns:
        Similarity score (0.0 - 1.0)
    """
    from ..preprocessing.normalize import normalize_name_by_type

    if not name1 or not name2:
        return 0.0

    # Normalize names (removes titles for PERSON)
    name1_norm = normalize_name_by_type(name1, entity_type)
    name2_norm = normalize_name_by_type(name2, entity_type)

    # Then compare
    name1_norm = name1_norm.lower().strip()
    name2_norm = name2_norm.lower().strip()

    # Use fuzz.ratio for exact matching
    return fuzz.ratio(name1_norm, name2_norm) / 100.0


def compute_alias_similarity(aliases1: list[str], aliases2: list[str]) -> float:
    """
    Compute alias overlap similarity.

    Args:
        aliases1: First person's aliases
        aliases2: Second person's aliases

    Returns:
        Jaccard similarity (0.0 - 1.0)
    """
    if not aliases1 or not aliases2:
        return 0.0

    # Normalize aliases
    set1 = {alias.lower().strip() for alias in aliases1}
    set2 = {alias.lower().strip() for alias in aliases2}

    # Jaccard similarity
    intersection = set1 & set2
    union = set1 | set2

    if not union:
        return 0.0

    return len(intersection) / len(union)


def validate_person_cluster(
    cluster_items: list[dict],
    min_name_similarity: float = 0.80,
    min_alias_similarity: float = 0.50,
) -> tuple[bool, str]:
    """
    Validate PERSON cluster using fuzzy matching.

    Args:
        cluster_items: List of PERSON items in cluster
        min_name_similarity: Minimum name similarity threshold
        min_alias_similarity: Minimum alias similarity threshold

    Returns:
        (is_valid, reason)
    """
    if len(cluster_items) <= 1:
        return True, "singleton"

    # Check pairwise similarities
    for i, item_a in enumerate(cluster_items):
        for item_b in cluster_items[i+1:]:
            name_a = item_a["payload"]["properties"].get("name", "")
            name_b = item_b["payload"]["properties"].get("name", "")

            aliases_a = item_a["payload"]["properties"].get("aliases") or []
            aliases_b = item_b["payload"]["properties"].get("aliases") or []

            # Compute similarities
            name_sim = compute_name_similarity(name_a, name_b, entity_type="PERSON")
            alias_sim = compute_alias_similarity(aliases_a, aliases_b)

            # Decision logic
            if name_sim < min_name_similarity and alias_sim < min_alias_similarity:
                # Both low → not similar enough
                return False, f"Low similarity: name={name_sim:.2f}, alias={alias_sim:.2f} ({name_a} vs {name_b})"

    return True, "valid"


def split_person_cluster_by_similarity(
    cluster_items: list[dict],
    min_name_similarity: float = 0.80,
    min_alias_similarity: float = 0.50,
) -> list[list[dict]]:
    """
    Split PERSON cluster into sub-clusters based on similarity.

    Uses graph connectivity: persons are connected if similar enough.

    Args:
        cluster_items: List of PERSON items in cluster
        min_name_similarity: Minimum name similarity threshold
        min_alias_similarity: Minimum alias similarity threshold

    Returns:
        List of sub-clusters
    """
    if len(cluster_items) <= 1:
        return [cluster_items]

    # Build similarity graph
    n = len(cluster_items)
    graph = defaultdict(set)

    for i in range(n):
        for j in range(i+1, n):
            item_a = cluster_items[i]
            item_b = cluster_items[j]

            # Check source constraint first - never connect same source
            source_a = item_a["payload"]["properties"].get("source_document_id", "")
            source_b = item_b["payload"]["properties"].get("source_document_id", "")

            if source_a == source_b:
                # Same source, don't connect
                continue

            name_a = item_a["payload"]["properties"].get("name", "")
            name_b = item_b["payload"]["properties"].get("name", "")

            aliases_a = item_a["payload"]["properties"].get("aliases") or []
            aliases_b = item_b["payload"]["properties"].get("aliases") or []

            # Compute similarities
            name_sim = compute_name_similarity(name_a, name_b, entity_type="PERSON")
            alias_sim = compute_alias_similarity(aliases_a, aliases_b)

            # Add edge if similar enough
            if name_sim >= min_name_similarity or alias_sim >= min_alias_similarity:
                graph[i].add(j)
                graph[j].add(i)

    # Find connected components (BFS)
    visited = set()
    components = []

    for i in range(n):
        if i in visited:
            continue

        # BFS
        component = []
        queue = [i]
        visited.add(i)

        while queue:
            current = queue.pop(0)
            component.append(cluster_items[current])

            for neighbor in graph[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        components.append(component)

    return components


def validate_source_constraint(
    cluster_items: list[dict],
) -> tuple[bool, str]:
    """
    Validate source constraint: no two entities from same source.

    Args:
        cluster_items: List of items in cluster

    Returns:
        (is_valid, reason)
    """
    if len(cluster_items) <= 1:
        return True, "singleton"

    # Check for duplicate sources
    sources = [item["payload"]["properties"]["source_document_id"] for item in cluster_items]
    source_counts = defaultdict(int)

    for source in sources:
        source_counts[source] += 1

    # Find violations
    violations = [source for source, count in source_counts.items() if count > 1]

    if violations:
        return False, f"Source constraint violated: {violations[0]} has {source_counts[violations[0]]} entities"

    return True, "valid"
