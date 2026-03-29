from __future__ import annotations  # FIX: phải là dòng đầu tiên trong file

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Optional

from entity_linkingv2.entity_store import EntityDB
from entity_linkingv2.prompt import get_entity_link_prompt
from llms.factory import get_llm


@dataclass
class MergeDecision:
    """One LLM merge decision: seed absorbs candidate."""
    seed_id:           str
    absorb_id:         str
    merged_properties: dict
    confidence:        float
    reason:            str
    score:             float   # cosine similarity from vector search

class UnionFind:
    """
    Path-compressed Union-Find.
    Convention: union(canonical, absorbed) — canonical wins.
    """
 
    def __init__(self):
        self.parent: dict[str, str] = {}
 
    def find(self, x: str) -> str:
        if x not in self.parent:
            self.parent[x] = x
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])   # path compression
        return self.parent[x]
 
    def union(self, canonical: str, absorbed: str):
        rc = self.find(canonical)
        ra = self.find(absorbed)
        if rc != ra:
            self.parent[ra] = rc    # absorbed → canonical
 
    def all_nodes(self) -> list[str]:
        return list(self.parent.keys())


def merge_properties(base: dict, other: dict) -> dict:
    """
    Merge two property dicts:
      - lists  → union (deduplicated, order preserved)
      - strings → keep the longer / more complete value
      - None   → prefer non-null
    """
    result = dict(base)
    for key, val in other.items():
        if val is None:
            continue
        existing = result.get(key)
        if existing is None:
            result[key] = val
        elif isinstance(existing, list):
            merged = list(existing)
            items = val if isinstance(val, list) else [val]
            for v in items:
                if v not in merged:
                    merged.append(v)
            result[key] = merged
        elif isinstance(existing, str) and isinstance(val, str):
            # Prefer longer (more complete) string
            result[key] = val if len(val) > len(existing) else existing
    return result

def pair_key(a: str, b: str) -> tuple[str, str]:
    """Normalised pair so (A,B) == (B,A) de tranh trung lap cap key."""
    return (min(a, b), max(a, b))


def _call_llm(prompt: str) -> str:
    result  = get_llm("proxypal", model_name="gpt-5").generate(prompt)
    content = result.content

    # Anthropic-style: content là list[ContentBlock]
    if isinstance(content, list):
        content = "".join(
            (b.text if hasattr(b, "text") else b.get("text", ""))
            for b in content
        )

    content = str(content).strip()

    if not content:
        # Log raw result để debug khi API trả rỗng
        raise ValueError(f"LLM returned empty content. Raw result: {result!r}")

    return content


def _parse_llm_response(raw: str) -> dict:
    # Strip markdown code fences nếu có
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())



def ask_llm_for_pair(
    seed: dict,
    candidate: dict,
    max_retries: int = 2,
) -> Optional[MergeDecision]:
    """
    Call LLM for one (seed, candidate) pair.
    Returns MergeDecision if merge, None if skip or error.
    """
    prompt = get_entity_link_prompt(seed, candidate)
 
    for attempt in range(max_retries + 1):
        try:
            raw  = _call_llm(prompt)
            data = _parse_llm_response(raw)
 
            if not data.get("merge", False):
                return None     # LLM decided: skip
 
            return MergeDecision(
                seed_id=seed["entity_id"],
                absorb_id=candidate["entity_id"],
                merged_properties=data.get("merged_properties", {}),
                confidence=float(data.get("confidence", 0.0)),
                reason=data.get("reason", ""),
                score=float(candidate.get("_score", 0.0)),
            )
 
        except (json.JSONDecodeError, KeyError, Exception) as e:
            if attempt < max_retries:
                print(f"LLM attempt {attempt+1} failed, retrying: {e}")
            else:
                print(
                    f"LLM failed for ({seed.get('entity_id')}, "
                    f"{candidate.get('entity_id')}): {e}"
                )
    return None
     
     
# ══════════════════════════════════════════════════════════════════════════════
# Phase 1 — Read: collect candidate pairs
# ══════════════════════════════════════════════════════════════════════════════
 
def phase1_collect_pairs(
    store:           EntityDB,
    attempted_pairs: set,
    limit:           int   = 10,
    score_threshold: float = 0.85,
    batch_size:      int   = 256,
    filter_label:    bool  = True,
) -> list[tuple[dict, dict]]:
    """
    Scroll all entities. For each seed, search similar candidates.
    Dedup via attempted_pairs (persists across iterations).
 
    Args:
        filter_label: If True, only consider candidates with the same label
                      (more precise). Cross-label is handled in Phase 5.
 
    Returns:
        task_queue: list of (seed, candidate) tuples not yet attempted.
    """
    task_queue: list[tuple[dict, dict]] = []
 
    for seed in store.iter_entities(batch_size=batch_size):
        seed_id     = seed.get("entity_id", "")
        seed_labels = set(seed.get("labels", []))
        if not seed_id:
            continue
 
        # Get top-K similar entities (same label if filter_label=True)
        label_hint = seed.get("labels", [None])[0] if filter_label else None
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
 
            # Label check (double safety if Qdrant filter wasn't used)
            if filter_label and set(candidate.get("labels", [])) != seed_labels:
                continue
 
            pk = pair_key(seed_id, cid)
            if pk not in attempted_pairs:
                attempted_pairs.add(pk)
                task_queue.append((seed, candidate))
 
    print(f"Phase 1: {len(task_queue)} new pairs | "
                f"attempted_pairs total: {len(attempted_pairs)}")
    return task_queue
 
 
# ══════════════════════════════════════════════════════════════════════════════
# Phase 2 — LLM gate (parallel, read-only)
# ══════════════════════════════════════════════════════════════════════════════
 
def phase2_llm_gate(
    task_queue:  list[tuple[dict, dict]],
    max_workers: int = 8,
) -> list[MergeDecision]:
    """
    Submit ALL pairs to thread pool concurrently.
    Wait for EVERY future before returning.
    Qdrant is NOT touched here.
 
    Returns:
        decisions: only MERGE decisions (skips are silently discarded).
    """
    if not task_queue:
        return []
 
    decisions: list[MergeDecision] = []
 
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(ask_llm_for_pair, seed, candidate): (seed_id, cid)
            for seed, candidate in task_queue
            for seed_id, cid in [(seed["entity_id"], candidate["entity_id"])]
        }
        for future in as_completed(futures):
            result = future.result()
            if result is not None:
                decisions.append(result)
 
    print(f"Phase 2: {len(decisions)} merge decisions "
                f"out of {len(task_queue)} pairs")
    return decisions
 
 
# ══════════════════════════════════════════════════════════════════════════════
# Phase 3 — Build merge plan (Union-Find, in-memory)
# ══════════════════════════════════════════════════════════════════════════════
 
def phase3_build_plan(decisions: list[MergeDecision]) -> dict[str, dict]:
    """
    Resolve transitive chains using Union-Find.

    Example:
        decisions = [A→B, B→C, D→E]
        After union: find(B)=A, find(C)=A  →  plan[A]={absorbed:[B,C]}
                     find(E)=D             →  plan[D]={absorbed:[E]}

    Why this matters:
        If we process A→B and B→C separately, C might not get remapped to A.
        Union-Find handles transitive closure in one pass.
    """
    if not decisions:
        return {}
 
    uf   = UnionFind()
    props: dict[str, dict] = {}     # accumulated merged properties per canonical
 
    for d in decisions:
        uf.union(d.seed_id, d.absorb_id)
        canonical = uf.find(d.seed_id)
        props[canonical] = merge_properties(
            props.get(canonical, {}),
            d.merged_properties,
        )
 
    plan: dict[str, dict] = {}
    for node_id in uf.all_nodes():
        canonical = uf.find(node_id)
        if node_id != canonical:
            plan.setdefault(canonical, {
                "absorbed":   [],
                "properties": props.get(canonical, {}),
            })
            plan[canonical]["absorbed"].append(node_id)
 
    print(f"Phase 3: {len(plan)} canonical groups "
                f"| absorbed total: {sum(len(v['absorbed']) for v in plan.values())}")
    return plan
 
 
# ══════════════════════════════════════════════════════════════════════════════
# Phase 4 — Bulk write (single write phase per iteration)
# ══════════════════════════════════════════════════════════════════════════════
 
def phase4_bulk_write(
    store:         EntityDB,
    plan:          dict[str, dict],
    canonical_map: dict[str, str],
) -> int:
    """
    Apply merge plan atomically:
      1. For each canonical: fetch current data, merge all absorbed props,
         upsert with NEW embedding (re-embed from merged text).
      2. Update canonical_map.
      3. Batch-delete all absorbed entities in one Qdrant call.
 
    Returns:
        Number of canonical groups written (= n_merges).
    """
    if not plan:
        return 0
 
    all_absorbed: list[str] = []
 
    for canonical_id, entry in plan.items():
        absorbed  = entry["absorbed"]
        llm_props = entry["properties"]
 
        # ── Fetch current canonical from Qdrant ────────────────────────
        current = store.get_entity_by_id(canonical_id)
        if current is None:
            print(f"Canonical {canonical_id} not found in Qdrant — skipping")
            continue
 
        # ── Merge: current ← llm decision ← each absorbed entity ──────
        final_props = merge_properties(current.get("properties", {}), llm_props)
        final_labels: list[str] = list(current.get("labels", []))
        existing_merged_ids: list[str] = list(current.get("merged_ids", []))
 
        for absorbed_id in absorbed:
            absorbed_entity = store.get_entity_by_id(absorbed_id)
            if absorbed_entity:
                final_props = merge_properties(
                    final_props,
                    absorbed_entity.get("properties", {}),
                )
                for lbl in absorbed_entity.get("labels", []):
                    if lbl not in final_labels:
                        final_labels.append(lbl)
 
        # ── Upsert canonical with NEW embedding (key fix vs old pipeline) ──
        updated_entity = {
            "id":         canonical_id,
            "labels":     final_labels,
            "properties": final_props,
            "merged_ids": existing_merged_ids + absorbed,
        }
        store.upsert_entities([updated_entity])
 
        # ── Update canonical_map ────────────────────────────────────────
        for absorbed_id in absorbed:
            canonical_map[absorbed_id] = canonical_id
 
        all_absorbed.extend(absorbed)
        print(f"  {canonical_id} ← absorbed {absorbed}")
 
    # ── Single batch delete ────────────────────────────────────────────
    if all_absorbed:
        store.delete_entities(all_absorbed)
 
    print(f"Phase 4: {len(plan)} merges applied | "
                f"{len(all_absorbed)} entities deleted | "
                f"canonical_map size: {len(canonical_map)}")
    return len(plan)
 
 
# ══════════════════════════════════════════════════════════════════════════════
# Phase 5 — Cross-label sweep (runs once after convergence)
# ══════════════════════════════════════════════════════════════════════════════
 
def phase5_cross_label_sweep(
    store:           EntityDB,
    canonical_map:   dict[str, str],
    score_threshold: float = 0.95,
    batch_size:      int   = 256,
    max_workers:     int   = 8,
) -> int:
    """
    One-time sweep without label filter.
    Only considers (seed, candidate) pairs with DIFFERENT labels.
    High threshold (0.95) to avoid false positives.
 
    Catches entities that were mislabeled during extraction.
 
    Returns:
        Number of cross-label merges applied.
    """
    cross_attempted: set = set()
    task_queue: list[tuple[dict, dict]] = []
 
    for seed in store.iter_entities(batch_size=batch_size):
        seed_id     = seed.get("entity_id", "")
        seed_labels = set(seed.get("labels", []))
        if not seed_id:
            continue
 
        candidates = store.search_similar(
            seed_entity=seed,
            limit=5,
            score_threshold=score_threshold,
            label_filter=None,      # no label filter
        )
 
        for candidate in candidates:
            cid = candidate.get("entity_id", "")
            if not cid or cid == seed_id:
                continue
 
            # Only cross-label pairs
            if set(candidate.get("labels", [])) == seed_labels:
                continue
 
            pk = pair_key(seed_id, cid)
            if pk not in cross_attempted:
                cross_attempted.add(pk)
                task_queue.append((seed, candidate))
 
    if not task_queue:
        print("Phase 5: No cross-label candidates — skipping")
        return 0
 
    print(f"Phase 5: {len(task_queue)} cross-label pairs to evaluate")
 
    decisions = phase2_llm_gate(task_queue, max_workers)
    if not decisions:
        return 0
 
    plan = phase3_build_plan(decisions)
    return phase4_bulk_write(store, plan, canonical_map)
 


# ══════════════════════════════════════════════════════════════════════════════
# Main entry point
# ══════════════════════════════════════════════════════════════════════════════
 
def run_entity_linking(
    store:                 EntityDB,
    max_iterations:        int   = 5,
    limit:                 int   = 10,
    score_threshold:       float = 0.85,
    max_workers:           int   = 8,
    batch_size:            int   = 256,
    cross_label_threshold: float = 0.95,
) -> dict[str, str]:
    """
    Run the full entity linking pipeline (Phase 1–5).
 
    Returns:
        canonical_map: {old_entity_id → canonical_entity_id}
        Use this map in Phase 6 (rewrite_kg_files) to remap all IDs.
    """
    canonical_map:   dict[str, str] = {}
    attempted_pairs: set            = set()
 
    # ── Iterative loop: Phase 1 → 2 → 3 → 4 ─────────────────────────────────
    for iteration in range(1, max_iterations + 1):
        print(f"{'='*50}")
        print(f"Iteration {iteration}/{max_iterations}")
 
        # Phase 1
        task_queue = phase1_collect_pairs(
            store, attempted_pairs,
            limit=limit,
            score_threshold=score_threshold,
            batch_size=batch_size,
        )
        if not task_queue:
            print("Phase 1: No new pairs — converged early")
            break
 
        # Phase 2
        decisions = phase2_llm_gate(task_queue, max_workers)
        if not decisions:
            print("Phase 2: No merge decisions — converged")
            break
 
        # Phase 3
        plan = phase3_build_plan(decisions)
 
        # Phase 4
        n_merges = phase4_bulk_write(store, plan, canonical_map)
        if n_merges == 0:
            print("Phase 4: Nothing written — converged")
            break
 
    # ── Phase 5: Cross-label (once) ───────────────────────────────────────────
    print(f"{'='*50}")
    phase5_cross_label_sweep(
        store, canonical_map,
        score_threshold=cross_label_threshold,
        batch_size=batch_size,
        max_workers=max_workers,
    )
 
    print(f"Entity linking complete | "
                f"total remapped IDs: {len(canonical_map)}")
    return canonical_map