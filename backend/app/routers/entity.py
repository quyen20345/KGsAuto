from fastapi import APIRouter
from app.db.neo4j import get_driver

router = APIRouter(prefix="/api", tags=["entity"])


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


@router.get("/entity/{entity_id}")
def get_entity_details(entity_id: str):
    query = """
    MATCH (n) WHERE n.id = $entity_id
    OPTIONAL MATCH (n)-[r_out]->(m_out)
    OPTIONAL MATCH (m_in)-[r_in]->(n)
    RETURN n.id AS id, n.name AS name, labels(n) AS labels, properties(n) AS properties,
           collect(DISTINCT {type: type(r_out), target_id: m_out.id, target_name: m_out.name}) AS outgoing,
           collect(DISTINCT {type: type(r_in), target_id: m_in.id, target_name: m_in.name}) AS incoming
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
