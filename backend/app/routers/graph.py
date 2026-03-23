from fastapi import APIRouter
from ..db.neo4j import get_driver
from ..schemas.entity import QueryModel

router = APIRouter(prefix="/api", tags=["graph"])


@router.post("/query")
def run_custom_cypher(req: QueryModel):
    driver = get_driver()
    data = []
    try:
        with driver.session() as session:
            results = session.run(req.cypher)
            for record in results:
                data.append(record.data())
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/random_triplets")
def get_random_triplets(limit: int = 10):
    query = """
    MATCH (n)-[r]->(m)
    WITH n, r, m, rand() as random
    ORDER BY random
    LIMIT $limit
    RETURN n.id AS source_id, coalesce(n.name, n.id) AS source_name, labels(n)[0] AS source_label,
           type(r) AS rel_type,
           m.id AS target_id, coalesce(m.name, m.id) AS target_name, labels(m)[0] AS target_label
    """
    driver = get_driver()
    try:
        with driver.session() as session:
            results = session.run(query, {"limit": limit})
            data = [
                {
                    "source_id": r["source_id"],
                    "source_name": r["source_name"],
                    "source_label": r["source_label"],
                    "rel_type": r["rel_type"],
                    "target_id": r["target_id"],
                    "target_name": r["target_name"],
                    "target_label": r["target_label"],
                }
                for r in results
            ]
        return data
    except Exception as e:
        return {"error": str(e)}
