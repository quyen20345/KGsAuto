from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from ..storage.entity_store import EntityDB


@dataclass
class PairItem:
    pair_id: int
    seed: dict[str, Any]
    candidate: dict[str, Any]
    score: float
    status: str = "pending"  # pending|merged|skipped
    decision: Optional[str] = None
    canonical_id: Optional[str] = None
    merged_properties: Optional[dict[str, Any]] = None



def pair_key(a: str, b: str) -> tuple[str, str]:
    return (min(a, b), max(a, b))


def collect_pairs(
    store: EntityDB,
    *,
    limit: int,
    score_threshold: float,
    batch_size: int = 256,
) -> list[PairItem]:
    attempted: set[tuple[str, str]] = set()
    pairs: list[PairItem] = []
    pair_id = 1

    for seed in store.iter_entities(batch_size=batch_size):
        seed_id = seed.get("entity_id", "")
        seed_labels = set(seed.get("labels", []))
        if not seed_id:
            continue

        label_hint = seed.get("labels", [None])[0]
        candidates = store.search_similar(
            seed_entity=seed,
            limit=limit,
            score_threshold=score_threshold,
            label_filter=label_hint,
        )

        for candidate in candidates:
            cid = candidate.get("entity_id", "")
            if not cid or cid == seed_id:
                continue
            if set(candidate.get("labels", [])) != seed_labels:
                continue

            key = pair_key(seed_id, cid)
            if key in attempted:
                continue
            attempted.add(key)

            pairs.append(
                PairItem(
                    pair_id=pair_id,
                    seed=seed,
                    candidate=candidate,
                    score=float(candidate.get("_score", 0.0)),
                )
            )
            pair_id += 1

    return pairs