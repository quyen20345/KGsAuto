from __future__ import annotations

import math
from collections import defaultdict

from ..types import ClusterAssignment

try:
    from sklearn.cluster import HDBSCAN as SklearnHDBSCAN
except Exception:  # pragma: no cover
    SklearnHDBSCAN = None


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _fallback_cluster(items: list[dict], similarity_threshold: float) -> tuple[list[int], list[float]]:
    """
    Greedy graph-components clustering using cosine threshold.
    """
    n = len(items)
    if n == 0:
        return [], []

    adj: list[list[int]] = [[] for _ in range(n)]
    vectors = [x["vector"] for x in items]
    for i in range(n):
        for j in range(i + 1, n):
            sim = _cosine(vectors[i], vectors[j])
            if sim >= similarity_threshold:
                adj[i].append(j)
                adj[j].append(i)

    labels = [-1] * n
    probs = [0.0] * n
    cluster_id = 0
    for i in range(n):
        if labels[i] != -1:
            continue
        stack = [i]
        component: list[int] = []
        labels[i] = cluster_id
        while stack:
            u = stack.pop()
            component.append(u)
            for v in adj[u]:
                if labels[v] == -1:
                    labels[v] = cluster_id
                    stack.append(v)

        if len(component) == 1:
            labels[component[0]] = -1
            probs[component[0]] = 0.0
        else:
            for idx in component:
                probs[idx] = 0.9
            cluster_id += 1

    return labels, probs


def cluster_embeddings(
    items: list[dict],
    min_cluster_size: int,
    min_samples: int,
    similarity_threshold: float,
    by_primary_type: bool = True,
) -> list[ClusterAssignment]:
    groups: dict[str, list[dict]] = defaultdict(list)
    if by_primary_type:
        for item in items:
            ptype = str(item.get("payload", {}).get("primary_type", "UNKNOWN"))
            groups[ptype].append(item)
    else:
        groups["ALL"] = list(items)

    assignments: list[ClusterAssignment] = []
    cluster_offsets: dict[str, int] = defaultdict(int)

    for ptype, gitems in groups.items():
        if not gitems:
            continue

        if SklearnHDBSCAN is not None and len(gitems) >= max(2, min_cluster_size):
            model = SklearnHDBSCAN(
                min_cluster_size=min_cluster_size,
                min_samples=min_samples,
                metric="cosine",  # Changed from "euclidean" for consistency with fallback
                allow_single_cluster=True,
            )
            vectors = [x["vector"] for x in gitems]
            labels = list(model.fit_predict(vectors))
            probabilities = list(getattr(model, "probabilities_", [1.0] * len(gitems)))
        else:
            labels, probabilities = _fallback_cluster(gitems, similarity_threshold)

        label_remap: dict[int, str] = {}
        next_local = cluster_offsets[ptype]

        for item, label, prob in zip(gitems, labels, probabilities):
            if label == -1:
                cid = "noise"
                confidence = 0.0
            else:
                if label not in label_remap:
                    label_remap[label] = f"{ptype.lower()}_{next_local:04d}"
                    next_local += 1
                cid = label_remap[label]
                confidence = float(prob)

            assignments.append(
                ClusterAssignment(
                    node_id=item["node_id"],
                    cluster_id=cid,
                    probability=confidence,
                    primary_type=ptype,
                )
            )

        cluster_offsets[ptype] = next_local

    return assignments
