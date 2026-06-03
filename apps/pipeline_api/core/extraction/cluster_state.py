"""Cluster-local context state for extraction."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ClusterState:
    cluster_name: str
    entity_records: list[str] = field(default_factory=list)
    summary_facts: list[str] = field(default_factory=list)

    def add_result(self, result: dict[str, Any]) -> None:
        for node in result.get("nodes", []):
            record = _node_to_record(node)
            if record and record not in self.entity_records:
                self.entity_records.append(record)

            fact = _node_to_fact(node)
            if fact:
                self.record_fact(fact)

        for relationship in result.get("relationships", []):
            fact = _relationship_to_fact(relationship)
            if fact:
                self.record_fact(fact)

    def sample_entity_records(self, limit: int) -> list[str]:
        if limit <= 0:
            return []
        return self.entity_records[:limit]

    def record_fact(self, fact: str) -> None:
        cleaned = fact.strip()
        if cleaned and cleaned not in self.summary_facts:
            self.summary_facts.append(cleaned)

    def get_summary(self, max_items: int) -> list[str]:
        if max_items <= 0:
            return []
        return self.summary_facts[-max_items:]


def _node_to_record(node: dict[str, Any]) -> str | None:
    properties = node.get("properties", {})
    name = properties.get("name")
    node_id = node.get("id")
    if not name or not node_id:
        return None

    aliases = properties.get("aliases", [])
    aliases_text = ", ".join(alias for alias in aliases if alias)
    if aliases_text:
        return f"{name} | {node_id} | aliases: {aliases_text}"
    return f"{name} | {node_id}"


def _node_to_fact(node: dict[str, Any]) -> str | None:
    properties = node.get("properties", {})
    name = properties.get("name")
    labels = node.get("labels") or []
    label = labels[0] if labels else "ENTITY"
    description = properties.get("description")
    if not name:
        return None
    if description:
        return f"{label}: {name} — {description}"
    return f"{label}: {name}"


def _relationship_to_fact(relationship: dict[str, Any]) -> str | None:
    rel_type = relationship.get("type")
    source = relationship.get("source")
    target = relationship.get("target")
    if not rel_type or not source or not target:
        return None
    return f"REL: {source} -[{rel_type}]-> {target}"
