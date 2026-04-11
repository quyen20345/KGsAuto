from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class NodeRecord:
    node_id: str
    labels: list[str]
    properties: dict[str, Any]
    source_file: str


@dataclass
class EmbeddedNode:
    node_id: str
    vector: list[float]
    payload: dict[str, Any]


@dataclass
class ClusterAssignment:
    node_id: str
    cluster_id: str
    probability: float
    primary_type: str


@dataclass
class Stage1Result:
    run_id: str
    collection_name: str
    indexed_nodes: int
    index_path: str


@dataclass
class Stage2Result:
    run_id: str
    collection_name: str
    assignments_path: str
    clusters_total: int
    noise_total: int


@dataclass
class Stage3Result:
    run_id: str
    decisions_path: str
    id_remap_path: str
    rewire_audit_path: str
    output_dir: str
