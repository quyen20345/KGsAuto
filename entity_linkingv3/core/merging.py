from __future__ import annotations
from typing import Any

from ..storage.entity_store import EntityDB

class UnionFind:
    def __init__(self):
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        if x not in self.parent:
            self.parent[x] = x
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, canonical: str, absorbed: str) -> None:
        rc = self.find(canonical)
        ra = self.find(absorbed)
        if rc != ra:
            self.parent[ra] = rc

    def all_nodes(self) -> list[str]:
        return list(self.parent.keys())


def merge_properties(base: dict[str, Any], other: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, val in other.items():
        if val is None:
            continue

        existing = result.get(key)
        if existing is None:
            result[key] = val
            continue

        if isinstance(existing, list):
            merged = list(existing)
            incoming = val if isinstance(val, list) else [val]
            for v in incoming:
                if v not in merged:
                    merged.append(v)
            result[key] = merged
            continue

        if isinstance(existing, str) and isinstance(val, str):
            result[key] = val if len(val) > len(existing) else existing
            continue

    return result


