from fastapi import APIRouter
from ..core.config import EMBEDDING_MODEL
from ..db.neo4j import get_driver
from ..schemas.entity import MergeEntityModel, MergeEntityResponse
import unicodedata

# Import for vector search
from services.entity_resolution.preprocessing.representation import get_embedding_model

router = APIRouter(prefix="/api", tags=["entity"])

# Cache for embedding model
_embedding_model = None


def _get_embedding_model():
    """Get cached embedding model."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = get_embedding_model(EMBEDDING_MODEL)
    return _embedding_model


def _strip_diacritics(text: str) -> str:
    """Remove Vietnamese diacritics for fuzzy matching."""
    if not text:
        return ""
    # NFD normalization separates base characters from diacritics
    normalized = unicodedata.normalize('NFD', text)
    # Filter out combining diacritical marks
    return ''.join(ch for ch in normalized if unicodedata.category(ch) != 'Mn')


def _merge_list_values(existing, incoming):
    existing_list = existing if isinstance(existing, list) else ([] if existing is None else [existing])
    incoming_list = incoming if isinstance(incoming, list) else ([] if incoming is None else [incoming])
    merged = []
    for value in existing_list + incoming_list:
        if value not in merged:
            merged.append(value)
    return merged


def _merge_node_properties(canonical_props: dict, duplicate_props: dict) -> dict:
    merged = dict(canonical_props)
    for key, value in duplicate_props.items():
        if key == "id" or value is None or value == "" or value == []:
            continue

        existing = merged.get(key)
        if key == "aliases":
            merged[key] = _merge_list_values(existing, value)
        elif existing is None or existing == "" or existing == []:
            merged[key] = value
        elif isinstance(existing, list) and isinstance(value, list):
            merged[key] = _merge_list_values(existing, value)
    return merged


def _merge_rel_properties(existing: dict, incoming: dict) -> dict:
    merged = dict(existing)
    for key, value in incoming.items():
        if key == "id" or value is None or value == "" or value == []:
            continue
        current = merged.get(key)
        if current is None or current == "" or current == []:
            merged[key] = value
        elif isinstance(current, list) and isinstance(value, list):
            merged[key] = _merge_list_values(current, value)
    return merged


def _merge_entity_transaction(tx, canonical_id: str, merge_ids: list[str]):
    canonical = tx.run(
        "MATCH (n:KgNode {id: $id}) RETURN n, labels(n) AS labels, properties(n) AS props",
        {"id": canonical_id},
    ).single()
    if not canonical:
        raise ValueError(f"Canonical node not found: {canonical_id}")

    canonical_props = dict(canonical["props"] or {})
    canonical_labels = [label for label in canonical["labels"] if label != "KgNode"]

    merged_ids = []

    for merge_id in merge_ids:
        if merge_id == canonical_id:
            continue

        duplicate = tx.run(
            "MATCH (n:KgNode {id: $id}) RETURN n, labels(n) AS labels, properties(n) AS props",
            {"id": merge_id},
        ).single()
        if not duplicate:
            continue

        duplicate_props = dict(duplicate["props"] or {})
        duplicate_labels = [label for label in duplicate["labels"] if label != "KgNode"]

        canonical_props = _merge_node_properties(canonical_props, duplicate_props)
        for label in duplicate_labels:
            if label not in canonical_labels:
                canonical_labels.append(label)

        outgoing = tx.run(
            "MATCH (d:KgNode {id: $merge_id})-[r]->(t) RETURN type(r) AS rel_type, properties(r) AS props, t.id AS target_id",
            {"merge_id": merge_id},
        )
        for row in outgoing:
            target_id = row["target_id"]
            if not target_id or target_id == canonical_id:
                continue
            rel_type = row["rel_type"]
            props = dict(row["props"] or {})
            existing = tx.run(
                f"MATCH (c:KgNode {{id: $canonical_id}})-[r:`{rel_type}`]->(t:KgNode {{id: $target_id}}) RETURN properties(r) AS props LIMIT 1",
                {"canonical_id": canonical_id, "target_id": target_id},
            ).single()
            merged_props = _merge_rel_properties(dict(existing["props"] or {}) if existing else {}, props)
            tx.run(
                f"MATCH (c:KgNode {{id: $canonical_id}}), (t:KgNode {{id: $target_id}}) MERGE (c)-[r:`{rel_type}`]->(t) SET r += $props",
                {"canonical_id": canonical_id, "target_id": target_id, "props": merged_props},
            )

        incoming = tx.run(
            "MATCH (s)-[r]->(d:KgNode {id: $merge_id}) RETURN type(r) AS rel_type, properties(r) AS props, s.id AS source_id",
            {"merge_id": merge_id},
        )
        for row in incoming:
            source_id = row["source_id"]
            if not source_id or source_id == canonical_id:
                continue
            rel_type = row["rel_type"]
            props = dict(row["props"] or {})
            existing = tx.run(
                f"MATCH (s:KgNode {{id: $source_id}})-[r:`{rel_type}`]->(c:KgNode {{id: $canonical_id}}) RETURN properties(r) AS props LIMIT 1",
                {"source_id": source_id, "canonical_id": canonical_id},
            ).single()
            merged_props = _merge_rel_properties(dict(existing["props"] or {}) if existing else {}, props)
            tx.run(
                f"MATCH (s:KgNode {{id: $source_id}}), (c:KgNode {{id: $canonical_id}}) MERGE (s)-[r:`{rel_type}`]->(c) SET r += $props",
                {"source_id": source_id, "canonical_id": canonical_id, "props": merged_props},
            )

        tx.run("MATCH (d:KgNode {id: $merge_id}) DETACH DELETE d", {"merge_id": merge_id})
        merged_ids.append(merge_id)

    set_clause = "SET c += $props"
    if canonical_labels:
        label_clause = ":".join(f"`{label}`" for label in canonical_labels)
        set_clause += f" SET c:{label_clause}"
    tx.run(
        f"MATCH (c:KgNode {{id: $canonical_id}}) {set_clause}",
        {"canonical_id": canonical_id, "props": canonical_props},
    )

    return {
        "canonical_id": canonical_id,
        "merged_ids": merged_ids,
        "deleted_ids": merged_ids,
    }


@router.post("/entity/merge", response_model=MergeEntityResponse)
def merge_entities(payload: MergeEntityModel):
    merge_ids = [merge_id for merge_id in payload.merge_ids if merge_id and merge_id != payload.canonical_id]
    if not merge_ids:
        return {"success": False, "error": "No valid merge_ids provided", "data": None}

    driver = get_driver()
    try:
        with driver.session() as session:
            data = session.execute_write(_merge_entity_transaction, payload.canonical_id, merge_ids)
        return {"success": True, "data": data, "error": None}
    except Exception as exc:
        return {"success": False, "data": None, "error": str(exc)}


@router.get("/search")
def search_entity(q: str):
    query = """
    MATCH (n)
    WHERE toLower(toString(n.name)) CONTAINS toLower($q)
       OR toLower(toString(n.id)) CONTAINS toLower($q)
    RETURN n.id AS id, n.name AS name, labels(n) AS labels LIMIT 20
    """
    driver = get_driver()
    with driver.session() as session:
        results = session.run(query, {"q": q})
        data = [{"id": r["id"], "name": r["name"], "labels": r["labels"]} for r in results]
    return data


@router.get("/search/lexical")
def search_entity_lexical(q: str, top_k: int = 10, label_filter: str = None):
    """
    Pure lexical search by name/aliases with diacritic normalization.

    Args:
        q: Search query
        top_k: Number of results to return
        label_filter: Optional comma-separated labels to filter (e.g., "ORGANIZATION,SCHOOL")
    """
    if not q or not q.strip():
        return []

    query_text = q.strip()
    query_normalized = _strip_diacritics(query_text.lower())
    query_tokens = set(query_normalized.split())

    driver = get_driver()

    # Fetch all candidates
    cypher = """
    MATCH (n)
    WHERE n.id IS NOT NULL
    RETURN n.id AS id,
           n.name AS name,
           labels(n) AS labels,
           properties(n) AS properties
    """

    with driver.session() as session:
        results = session.run(cypher)
        candidates = []

        for r in results:
            name = r["name"] or ""
            name_normalized = _strip_diacritics(name.lower())
            aliases = r["properties"].get("aliases", [])
            labels = r["labels"]

            # Apply label filter
            if label_filter:
                allowed_labels = set(l.strip().upper() for l in label_filter.split(","))
                if not any(label.upper() in allowed_labels for label in labels):
                    continue

            # Calculate match score
            score = 0.0

            # Exact match (highest priority)
            if name_normalized == query_normalized:
                score = 1.0
            # Contains query
            elif query_normalized in name_normalized:
                score = 0.9
            # Check aliases
            else:
                for alias in aliases:
                    alias_normalized = _strip_diacritics(str(alias).lower())
                    if alias_normalized == query_normalized:
                        score = max(score, 0.95)
                    elif query_normalized in alias_normalized:
                        score = max(score, 0.85)

            # Token overlap (all query tokens must appear in name)
            if score == 0.0 and query_tokens:
                name_tokens = set(name_normalized.split())
                if name_tokens:
                    overlap = len(query_tokens & name_tokens) / len(query_tokens)
                    score = overlap

            # Only include if there's a match
            if score > 0:
                candidates.append({
                    "id": r["id"],
                    "name": name,
                    "labels": labels,
                    "properties": r["properties"],
                    "score": score
                })

        # Sort by score descending
        candidates.sort(key=lambda x: x["score"], reverse=True)

        return [
            {
                "id": c["id"],
                "name": c["name"],
                "labels": c["labels"],
                "properties": c["properties"],
                "score": round(c["score"], 4)
            }
            for c in candidates[:top_k]
        ]


@router.get("/search/hybrid")
def search_entity_hybrid(q: str, top_k: int = 10, label_filter: str = None):
    """
    Hybrid search combining vector similarity + lexical matching.

    Args:
        q: Search query
        top_k: Number of results to return
        label_filter: Optional comma-separated labels to filter (e.g., "ORGANIZATION,SCHOOL")
    """
    if not q or not q.strip():
        return []

    query_text = q.strip()
    query_lower = query_text.lower()
    driver = get_driver()

    with driver.session() as session:
        index_check = session.run(
            "SHOW INDEXES YIELD name, state WHERE name = 'entity_embedding_index' RETURN state LIMIT 1"
        ).single()
        if not index_check:
            return []

        model = _get_embedding_model()
        query_embedding = model.encode(query_text, convert_to_numpy=True, show_progress_bar=False).tolist()

        # Get more candidates from vector search for reranking
        vector_top_k = min(top_k * 3, 100)

        results = session.run(
            """
            CALL db.index.vector.queryNodes('entity_embedding_index', $top_k, $query_embedding)
            YIELD node, score
            RETURN node.id AS id,
                   node.name AS name,
                   labels(node) AS labels,
                   properties(node) AS properties,
                   score
            """,
            {
                "top_k": vector_top_k,
                "query_embedding": query_embedding,
            },
        )

        candidates = []
        for r in results:
            candidates.append({
                "id": r["id"],
                "name": r["name"],
                "labels": r["labels"],
                "properties": r["properties"],
                "vector_score": float(r["score"]),
            })

    # Apply label filter if specified
    if label_filter:
        allowed_labels = set(l.strip().upper() for l in label_filter.split(","))
        candidates = [
            c for c in candidates
            if any(label.upper() in allowed_labels for label in c["labels"])
        ]

    # Rerank with hybrid scoring
    for candidate in candidates:
        name = candidate["name"] or ""
        name_lower = name.lower()
        aliases = candidate["properties"].get("aliases", [])

        # Normalize for diacritic-insensitive matching
        query_normalized = _strip_diacritics(query_lower)
        name_normalized = _strip_diacritics(name_lower)

        # Lexical scoring with normalization
        lexical_score = 0.0

        # Exact match (highest boost)
        if name_normalized == query_normalized:
            lexical_score = 1.0
        # Contains exact query
        elif query_normalized in name_normalized:
            lexical_score = 0.9
        # Check aliases
        elif aliases:
            for alias in aliases:
                alias_normalized = _strip_diacritics(str(alias).lower())
                if alias_normalized == query_normalized:
                    lexical_score = max(lexical_score, 0.95)
                elif query_normalized in alias_normalized:
                    lexical_score = max(lexical_score, 0.85)

        # Token overlap (also normalized)
        query_tokens = set(query_normalized.split())
        name_tokens = set(name_normalized.split())
        if query_tokens and name_tokens:
            overlap = len(query_tokens & name_tokens) / len(query_tokens)
            lexical_score = max(lexical_score, overlap * 0.7)

        # Adaptive hybrid scoring: boost lexical when it's strong
        candidate["lexical_score"] = lexical_score
        if lexical_score >= 0.8:
            # Strong lexical match: 40% vector + 60% lexical
            candidate["final_score"] = (0.4 * candidate["vector_score"]) + (0.6 * lexical_score)
        else:
            # Weak lexical match: 60% vector + 40% lexical
            candidate["final_score"] = (0.6 * candidate["vector_score"]) + (0.4 * lexical_score)

    # Sort by final score and return top_k
    candidates.sort(key=lambda x: x["final_score"], reverse=True)

    results = []
    for c in candidates[:top_k]:
        results.append({
            "id": c["id"],
            "name": c["name"],
            "labels": c["labels"],
            "properties": c["properties"],
            "score": round(c["final_score"], 4),
        })

    return results


@router.get("/entity/{entity_id}")
def get_entity_details(entity_id: str):
    query = """
    MATCH (n) WHERE n.id = $entity_id
    OPTIONAL MATCH (n)-[r_out]->(m_out)
    OPTIONAL MATCH (m_in)-[r_in]->(n)
    RETURN n.id AS id, n.name AS name, labels(n) AS labels, properties(n) AS properties,
           collect(DISTINCT {type: type(r_out), target_id: m_out.id, target_name: m_out.name, properties: properties(r_out)}) AS outgoing,
           collect(DISTINCT {type: type(r_in), target_id: m_in.id, target_name: m_in.name, properties: properties(r_in)}) AS incoming
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.run(query, {"entity_id": entity_id}).single()

    if not result or not result["id"]:
        return {"error": "Entity not found"}

    return {
        "id": result["id"],
        "name": result["name"],
        "labels": result["labels"],
        "properties": result["properties"],
        "outgoing": [rel for rel in result["outgoing"] if rel.get("target_id")],
        "incoming": [rel for rel in result["incoming"] if rel.get("target_id")],
    }


@router.get("/entity/{entity_id}")
def get_entity_details(entity_id: str):
    query = """
    MATCH (n) WHERE n.id = $entity_id
    OPTIONAL MATCH (n)-[r_out]->(m_out)
    OPTIONAL MATCH (m_in)-[r_in]->(n)
    RETURN n.id AS id, n.name AS name, labels(n) AS labels, properties(n) AS properties,
           collect(DISTINCT {type: type(r_out), target_id: m_out.id, target_name: m_out.name, properties: properties(r_out)}) AS outgoing,
           collect(DISTINCT {type: type(r_in), target_id: m_in.id, target_name: m_in.name, properties: properties(r_in)}) AS incoming
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.run(query, {"entity_id": entity_id}).single()

    if not result or not result["id"]:
        return {"error": "Entity not found"}

    return {
        "id": result["id"],
        "name": result["name"],
        "labels": result["labels"],
        "properties": result["properties"],
        "outgoing": [rel for rel in result["outgoing"] if rel.get("target_id")],
        "incoming": [rel for rel in result["incoming"] if rel.get("target_id")],
    }


@router.get("/entity/{entity_id}")
def get_entity_details(entity_id: str):
    query = """
    MATCH (n) WHERE n.id = $entity_id
    OPTIONAL MATCH (n)-[r_out]->(m_out)
    OPTIONAL MATCH (m_in)-[r_in]->(n)
    RETURN n.id AS id, n.name AS name, labels(n) AS labels, properties(n) AS properties,
           collect(DISTINCT {type: type(r_out), target_id: m_out.id, target_name: m_out.name, properties: properties(r_out)}) AS outgoing,
           collect(DISTINCT {type: type(r_in), target_id: m_in.id, target_name: m_in.name, properties: properties(r_in)}) AS incoming
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.run(query, {"entity_id": entity_id}).single()

    if not result or not result["id"]:
        return {"error": "Entity not found"}

    return {
        "id": result["id"],
        "name": result["name"],
        "labels": result["labels"],
        "properties": result["properties"],
        "outgoing": [rel for rel in result["outgoing"] if rel.get("target_id")],
        "incoming": [rel for rel in result["incoming"] if rel.get("target_id")],
    }
