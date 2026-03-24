import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from entity_linking.entity_store import EntityDB
from llms import get_llm

logger = logging.getLogger(__name__)


def _format_candidates(candidates: list[dict]) -> str:
    lines = []
    for i, c in enumerate(candidates, 1):
        props = c.get("properties", {})
        lines.append(f"--- Ứng viên {i} (score={c.get('_score', 0):.3f}) ---")
        lines.append(f"  id: {c.get('entity_id', '')}")
        lines.append(f"  labels: {c.get('labels', [])}")
        lines.append(f"  properties: {json.dumps(props, ensure_ascii=False, indent=4)}")
        lines.append("")
    return "\n".join(lines)


def _prepare_seed_for_prompt(entity: dict) -> dict:
    """
    Prepare seed entity for LLM prompt by extracting lifecycle context
    into separate _current_* keys so LLM can read them without confusion.

    Returns a new dict with:
    - _current_version: current version number
    - _existing_absorbed_ids: list of previously absorbed IDs
    - _existing_merge_history: list of previous merge events
    - properties: all other properties (excluding lifecycle fields)
    """
    props = entity.get("properties", {})

    # Extract lifecycle context
    prepared = {
        "entity_id": entity.get("entity_id", ""),
        "labels": entity.get("labels", []),
        "_current_version": props.get("version", 0),
        "_existing_absorbed_ids": props.get("absorbed_ids", []),
        "_existing_merge_history": props.get("merge_history", []),
        "properties": {}
    }

    # Copy all properties except lifecycle fields
    lifecycle_keys = {"version", "status", "merge_history", "absorbed_ids"}
    for key, value in props.items():
        if key not in lifecycle_keys:
            prepared["properties"][key] = value

    return prepared


def _inject_timestamps(result: dict) -> dict:
    """
    Replace all "__INJECT__" placeholders in LLM response with actual values:
    - event_id: uuid4()[:8]
    - merged_at: current UTC timestamp (ISO-8601)
    - updated_at: current UTC timestamp (ISO-8601)

    Now handles merge_history as array of strings (not objects).
    """
    from datetime import datetime, timezone
    from uuid import uuid4

    # Process result - deep copy
    result_copy = json.loads(json.dumps(result))
    now = datetime.now(timezone.utc).isoformat()

    # Inject timestamps in new_entity.properties.merge_history (array of strings)
    if result_copy.get("new_entity") and result_copy["new_entity"].get("properties"):
        props = result_copy["new_entity"]["properties"]
        if "merge_history" in props and isinstance(props["merge_history"], list):
            updated_history = []
            for item in props["merge_history"]:
                if isinstance(item, str):
                    # Replace __INJECT__ placeholders in string
                    # First occurrence (in [__INJECT__]) is event_id
                    # Second occurrence (merged_at=__INJECT__) is timestamp
                    updated_item = item
                    if "__INJECT__" in updated_item:
                        # Replace first __INJECT__ with event_id
                        updated_item = updated_item.replace("__INJECT__", str(uuid4())[:8], 1)
                    if "__INJECT__" in updated_item:
                        # Replace second __INJECT__ with timestamp
                        updated_item = updated_item.replace("__INJECT__", now, 1)
                    updated_history.append(updated_item)
                else:
                    # Keep non-string items as-is (shouldn't happen)
                    updated_history.append(item)
            props["merge_history"] = updated_history

    # Inject timestamps in ghost_updates
    if "ghost_updates" in result_copy and isinstance(result_copy["ghost_updates"], list):
        for ghost in result_copy["ghost_updates"]:
            if isinstance(ghost, dict) and ghost.get("updated_at") == "__INJECT__":
                ghost["updated_at"] = now

    return result_copy


def _ask_llm(llm, seed: dict, candidates: list[dict]) -> dict | None:
    """Send seed + candidates to LLM. Returns parsed response or None."""

    # Prepare seed with lifecycle context separated
    prepared_seed = _prepare_seed_for_prompt(seed)
    seed_json = json.dumps(prepared_seed, ensure_ascii=False, indent=2)

    # Import from entity_linking.prompt (not the inline ENTITY_LINK_PROMPT)
    from entity_linking.prompt import ENTITY_LINK_PROMPT

    prompt = ENTITY_LINK_PROMPT.format(
        seed_json=seed_json,
        candidates_text=_format_candidates(candidates),
    )

    response = llm.generate(prompt)
    raw = response.content.replace("```json", "").replace("```", "").strip()

    try:
        result = json.loads(raw)
        # Inject timestamps after parsing
        result = _inject_timestamps(result)
        return result
    except json.JSONDecodeError:
        logger.warning("Failed to parse LLM response for seed=%s", seed.get("entity_id"))
        return None

def _pair_key(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a <= b else (b, a)

def entity_link_iteration(
    store: EntityDB,
    llm,
    limit: int = 10,
    score_threshold: float = 0.85,
    max_workers: int = 8,
    batch_size: int = 256,
) -> int:
    """
    One pass:
    - Load entities by scroll payload (no N+1)
    - Build candidate list with attempted_pairs cache
    - Ask LLM concurrently
    - Apply merges sequentially + log linked entities
    """
    all_entities = [e for e in store.iter_entities(batch_size=batch_size) if e.get("entity_id")]
    processed = set()
    attempted_pairs = set()
    merges = 0

    future_map = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for seed in all_entities:
            seed_id = seed.get("entity_id", "")
            if not seed_id or seed_id in processed:
                continue

            seed_as_entity = {
                "id": seed_id,
                "labels": seed.get("labels", []),
                "properties": seed.get("properties", {}),
            }

            candidates = store.search_similar(seed_as_entity, limit=limit, score_threshold=score_threshold)
            filtered = []
            for c in candidates:
                cid = c.get("entity_id", "")
                if not cid or cid == seed_id or cid in processed:
                    continue

                key = _pair_key(seed_id, cid)
                if key in attempted_pairs:
                    continue
                attempted_pairs.add(key)
                filtered.append(c)

            if not filtered:
                continue

            fut = executor.submit(_ask_llm, llm, seed, filtered)
            future_map[fut] = (seed_id, filtered)

        for fut in as_completed(future_map):
            seed_id, _ = future_map[fut]

            try:
                result = fut.result()
            except Exception:
                logger.exception("LLM call failed for seed=%s", seed_id)
                continue

            if result is None:
                continue

            merge_ids = result.get("merge_ids", [])
            new_entity = result.get("new_entity")
            if not merge_ids or not new_entity:
                continue

            current_seed = store.get_entity_by_id(seed_id)
            if current_seed is None:
                continue

            valid_merge_ids = [
                mid for mid in merge_ids
                if mid and mid != seed_id and store.get_entity_by_id(mid) is not None
            ]
            if not valid_merge_ids:
                continue

            new_entity["id"] = seed_id  # enforce canonical id = seed id
            prev_merged = current_seed.get("merged_ids", [])
            new_entity["merged_ids"] = sorted(set(prev_merged + valid_merge_ids))

            store.upsert_entities([new_entity])

            # Process ghost_updates before hard-delete
            ghost_updates = result.get("ghost_updates", [])
            for ghost in ghost_updates:
                ghost_id = ghost.get("id")
                if not ghost_id:
                    continue

                # Get existing entity
                existing = store.get_entity_by_id(ghost_id)
                if existing is None:
                    logger.warning("Ghost entity not found: %s", ghost_id)
                    continue

                # Update properties with ghost metadata
                existing_props = existing.get("properties", {})
                existing_props["status"] = ghost.get("status", "merged")
                existing_props["merged_into"] = ghost.get("merged_into")
                existing_props["updated_at"] = ghost.get("updated_at")

                # Upsert the ghost entity with updated metadata
                ghost_entity = {
                    "id": ghost_id,
                    "labels": existing.get("labels", []),
                    "properties": existing_props
                }
                store.upsert_entities([ghost_entity])
                logger.info("[GHOST] Updated %s → merged_into=%s", ghost_id, ghost.get("merged_into"))

            # Then hard-delete
            store.delete_entities(valid_merge_ids)

            processed.add(seed_id)
            processed.update(valid_merge_ids)
            merges += len(valid_merge_ids)

            logger.info("[LINKED] canonical=%s merged=%s", seed_id, valid_merge_ids)

    logger.info(
        "Iteration summary: merges=%d, attempted_pairs=%d, seeds=%d",
        merges, len(attempted_pairs), len(all_entities)
    )
    return merges


def run_entity_linking(store: EntityDB, llm, max_iterations: int = 5, **kwargs) -> dict:
    """Run until convergence or max_iterations."""
    total = 0
    for i in range(1, max_iterations + 1):
        n = entity_link_iteration(store, llm, **kwargs)
        total += n
        logger.info("Iteration %d: %d merges", i, n)
        if n == 0:
            logger.info("Converged after %d iterations.", i)
            break

    remaining = len(store.get_all_entity_ids())
    return {"total_merges": total, "iterations": i, "remaining_entities": remaining}
