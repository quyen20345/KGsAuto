"""Sample triplets from the Neo4j knowledge graph."""

from typing import Any

from apps.graph_api.neo4j import get_driver
from services.triplet_evaluation.schemas import SampledTriplet


TRIPLET_RETURN_CLAUSE = """
WITH n, r, m, properties(n) AS source_props, properties(m) AS target_props
RETURN coalesce(source_props.id, elementId(n)) AS subject_id,
       coalesce(source_props.name, source_props.id, elementId(n)) AS subject_name,
       labels(n)[0] AS subject_label,
       source_props AS subject_properties,
       type(r) AS predicate,
       properties(r) AS rel_properties,
       coalesce(target_props.id, elementId(m)) AS object_id,
       coalesce(target_props.name, target_props.id, elementId(m)) AS object_name,
       labels(m)[0] AS object_label,
       target_props AS object_properties
"""

PREDICATE_QUERY = """
MATCH ()-[r]->()
WITH DISTINCT type(r) AS predicate
ORDER BY predicate
RETURN predicate
"""


def _to_plain_dict(value: Any) -> dict[str, Any]:
    """Convert Neo4j property objects to a regular dict."""
    return dict(value or {})


def _to_triplet(record: Any) -> SampledTriplet:
    return SampledTriplet(
        subject_id=str(record["subject_id"]),
        subject_name=str(record["subject_name"]),
        subject_label=record["subject_label"],
        subject_properties=_to_plain_dict(record["subject_properties"]),
        predicate=str(record["predicate"]),
        object_id=str(record["object_id"]),
        object_name=str(record["object_name"]),
        object_label=record["object_label"],
        object_properties=_to_plain_dict(record["object_properties"]),
        rel_properties=_to_plain_dict(record["rel_properties"]),
    )


def _predicate_filter_clause() -> str:
    return """
WHERE ($predicates IS NULL OR type(r) IN $predicates)
  AND ($exclude_predicates IS NULL OR NOT type(r) IN $exclude_predicates)
"""


def _random_query() -> str:
    return f"""
MATCH (n)-[r]->(m)
{_predicate_filter_clause()}
WITH n, r, m, rand() AS random
ORDER BY random
LIMIT $limit
{TRIPLET_RETURN_CLAUSE}
"""


def _predicate_query(predicate: str) -> str:
    return f"""
MATCH (n)-[r]->(m)
WHERE type(r) = $predicate
WITH n, r, m, rand() AS random
ORDER BY random
LIMIT $limit
{TRIPLET_RETURN_CLAUSE}
"""


def _normalize_filters(values: list[str] | tuple[str, ...] | None) -> list[str] | None:
    if not values:
        return None
    return list(values)


def sample_triplets(
    limit: int = 100,
    predicates: list[str] | tuple[str, ...] | None = None,
    exclude_predicates: list[str] | tuple[str, ...] | None = None,
) -> list[SampledTriplet]:
    """Return random triplets from Neo4j."""
    if limit < 1:
        raise ValueError("limit must be greater than 0")

    params = {
        "limit": limit,
        "predicates": _normalize_filters(predicates),
        "exclude_predicates": _normalize_filters(exclude_predicates),
    }
    driver = get_driver()
    with driver.session() as session:
        results = session.run(_random_query(), params)
        return [_to_triplet(record) for record in results]


def list_predicates() -> list[str]:
    """Return relationship types present in Neo4j."""
    driver = get_driver()
    with driver.session() as session:
        return [str(record["predicate"]) for record in session.run(PREDICATE_QUERY)]


def sample_triplets_by_predicate(
    per_predicate_limit: int,
    predicates: list[str] | tuple[str, ...] | None = None,
    exclude_predicates: list[str] | tuple[str, ...] | None = None,
) -> list[SampledTriplet]:
    """Return random triplets capped per relationship type."""
    if per_predicate_limit < 1:
        raise ValueError("per_predicate_limit must be greater than 0")

    included = set(predicates or list_predicates())
    excluded = set(exclude_predicates or [])
    selected_predicates = sorted(included - excluded)

    driver = get_driver()
    triplets: list[SampledTriplet] = []
    with driver.session() as session:
        for predicate in selected_predicates:
            results = session.run(
                _predicate_query(predicate),
                {"predicate": predicate, "limit": per_predicate_limit},
            )
            triplets.extend(_to_triplet(record) for record in results)
    return triplets


def sample_triplets_as_dicts(limit: int = 100) -> list[dict[str, Any]]:
    """Return random triplets as JSON-serializable dictionaries."""
    return [triplet.as_dict() for triplet in sample_triplets(limit)]
