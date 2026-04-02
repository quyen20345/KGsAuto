from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional
from uuid import uuid4

from .storage.entity_store import EntityDB
from .core.pairing import PairItem, collect_pairs
from .core.planing import build_pair_suggestion, build_merge_plan, apply_merge_plan
from .utils.rewrite import flatten_canonical_map, rewrite_kg_files
from .utils.loader import load_kg_files
from .utils.collector import collect_entities_from_kg_files 


class ServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass
class RunState:
    run_id: str
    input_dir: str
    collection_name: str
    kg_files: dict[str, dict[str, Any]]
    store: EntityDB
    score_threshold: float
    limit: int
    created_at: str
    pairs: list[PairItem] = field(default_factory=list)
    last_output_dir: Optional[str] = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class LinkingV3Service:
    def __init__(
        self,
        store_factory: Optional[Callable[[str], EntityDB]] = None,
        collection_prefix: str = "entities_store_v3_simple",
    ):
        self._run: Optional[RunState] = None
        self._collection_prefix = collection_prefix

        if store_factory is not None:
            self._store_factory = store_factory
        else:
            device = os.getenv("EL_DEVICE", "cpu")
            self._store_factory = lambda collection_name: EntityDB(collection_name=collection_name, device=device)

    def _ensure_run(self) -> RunState:
        if self._run is None:
            raise ServiceError("No active run. Please call /init first.", status_code=400)
        return self._run

    def _pair_to_dict(self, pair: PairItem, include_entities: bool = False) -> dict[str, Any]:
        payload = {
            "pair_id": pair.pair_id,
            "seed_id": pair.seed.get("entity_id", ""),
            "candidate_id": pair.candidate.get("entity_id", ""),
            "score": pair.score,
            "status": pair.status,
            "decision": pair.decision,
            "canonical_id": pair.canonical_id,
        }
        if include_entities:
            payload["seed"] = pair.seed
            payload["candidate"] = pair.candidate
            payload["merged_properties"] = pair.merged_properties
        return payload

    def _find_pair_or_404(self, pair_id: int) -> PairItem:
        run = self._ensure_run()
        for pair in run.pairs:
            if pair.pair_id == pair_id:
                return pair
        raise ServiceError(f"Pair {pair_id} not found", status_code=404)

    def prepare_run(
        self,
        *,
        input_dir: str,
        score_threshold: float = 0.85,
        limit: int = 10,
        collection_name: str | None = None,
    ) -> dict[str, Any]:
        kg_files = load_kg_files(input_dir)
        if not kg_files:
            raise ServiceError(f"No JSON files found in {input_dir}")

        entities = collect_entities_from_kg_files(kg_files)
        if not entities:
            raise ServiceError("No entities found in input graph files")

        chosen_collection = collection_name or f"{self._collection_prefix}_{uuid4().hex[:8]}"
        store = self._store_factory(chosen_collection)
        upserted = store.upsert_entities(entities)

        pairs = collect_pairs(
            store,
            limit=limit,
            score_threshold=score_threshold,
        )

        self._run = RunState(
            run_id=uuid4().hex[:10],
            input_dir=input_dir,
            collection_name=chosen_collection,
            kg_files=kg_files,
            store=store,
            score_threshold=score_threshold,
            limit=limit,
            created_at=_now_iso(),
            pairs=pairs,
        )

        return {
            "run_id": self._run.run_id,
            "input_dir": input_dir,
            "collection_name": chosen_collection,
            "entities": len(entities),
            "upserted": upserted,
            "pairs_total": len(pairs),
            "pairs": [self._pair_to_dict(p) for p in pairs[:50]],
            "max_iterations": 1,
        }

    def list_pairs(self, *, offset: int = 0, limit: int = 50) -> dict[str, Any]:
        run = self._ensure_run()
        sliced = run.pairs[offset:offset + limit]
        return {
            "run_id": run.run_id,
            "total": len(run.pairs),
            "offset": offset,
            "limit": limit,
            "items": [self._pair_to_dict(p) for p in sliced],
        }

    def get_pair(self, pair_id: int) -> dict[str, Any]:
        pair = self._find_pair_or_404(pair_id)
        suggested = build_pair_suggestion(pair)
        return {
            "pair": self._pair_to_dict(pair, include_entities=True),
            "seed": pair.seed,
            "candidate": pair.candidate,
            "suggested": suggested,
        }

    def review_pair(
        self,
        pair_id: int,
        *,
        decision: str,
        canonical_id: str | None = None,
        merged_properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        pair = self._find_pair_or_404(pair_id)
        normalized = decision.upper()

        if normalized not in {"MERGE", "SKIP"}:
            raise ServiceError("decision must be MERGE or SKIP")

        if normalized == "SKIP":
            pair.status = "skipped"
            pair.decision = "SKIP"
            pair.canonical_id = None
            pair.merged_properties = None
            return self._pair_to_dict(pair, include_entities=True)

        sid = pair.seed.get("entity_id")
        cid = pair.candidate.get("entity_id")
        chosen = canonical_id or sid
        if chosen not in {sid, cid}:
            raise ServiceError("canonical_id must be seed_id or candidate_id")

        suggested = build_pair_suggestion(pair)
        props = merged_properties if isinstance(merged_properties, dict) else suggested["merged_properties"]

        pair.status = "merged"
        pair.decision = "MERGE"
        pair.canonical_id = chosen
        pair.merged_properties = props

        return self._pair_to_dict(pair, include_entities=True)

    def apply_and_rewrite(self, *, output_dir: str) -> dict[str, Any]:
        run = self._ensure_run()

        merged_pairs = [p for p in run.pairs if p.status == "merged"]
        canonical_map: dict[str, str] = {}

        plan = build_merge_plan(merged_pairs, run.store)
        merges_applied = apply_merge_plan(run.store, plan, canonical_map)
        canonical_map = flatten_canonical_map(canonical_map)

        rewrite_stats = rewrite_kg_files(
            run.kg_files,
            run.store,
            canonical_map,
            output_dir,
        )

        run.last_output_dir = output_dir

        remap_path = Path(output_dir) / "id_remap.json"
        with open(remap_path, "w", encoding="utf-8") as f:
            json.dump(canonical_map, f, ensure_ascii=False, indent=2)

        return {
            "run_id": run.run_id,
            "output_dir": output_dir,
            "max_iterations": 1,
            "pairs_total": len(run.pairs),
            "pairs_merged": len(merged_pairs),
            "merges_applied": merges_applied,
            "canonical_map_size": len(canonical_map),
            "rewrite_stats": rewrite_stats,
            "id_remap_path": str(remap_path),
        }

    def reset(self, *, drop_collection: bool = True) -> dict[str, Any]:
        run = self._run
        if run and drop_collection:
            try:
                run.store.drop_collection()
            except Exception:
                pass

        previous = run.run_id if run else None
        self._run = None
        return {
            "ok": True,
            "dropped_collection": bool(run and drop_collection),
            "previous_run_id": previous,
        }

    def get_run_state(self) -> dict[str, Any]:
        if self._run is None:
            return {"active": False}

        run = self._run
        merged = sum(1 for p in run.pairs if p.status == "merged")
        skipped = sum(1 for p in run.pairs if p.status == "skipped")
        pending = sum(1 for p in run.pairs if p.status == "pending")

        return {
            "active": True,
            "run_id": run.run_id,
            "input_dir": run.input_dir,
            "collection_name": run.collection_name,
            "pairs_total": len(run.pairs),
            "pending": pending,
            "merged": merged,
            "skipped": skipped,
            "created_at": run.created_at,
            "last_output_dir": run.last_output_dir,
            "max_iterations": 1,
        }
