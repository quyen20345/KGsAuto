from fastapi import APIRouter
from typing import Optional
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
           type(r) AS rel_type, properties(r) AS rel_properties,
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
                    "rel_properties": r["rel_properties"],
                    "target_id": r["target_id"],
                    "target_name": r["target_name"],
                    "target_label": r["target_label"],
                }
                for r in results
            ]
        return data
    except Exception as e:
        return {"error": str(e)}


@router.get("/graph/metadata")
def get_graph_metadata():
    """Get all available node labels and relationship types in the graph"""
    driver = get_driver()
    try:
        with driver.session() as session:
            # Get all node labels
            labels_result = session.run("CALL db.labels() YIELD label RETURN collect(label) AS labels")
            labels = labels_result.single()["labels"]

            # Get all relationship types
            rels_result = session.run("CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) AS relationship_types")
            relationship_types = rels_result.single()["relationship_types"]

        return {
            "labels": labels,
            "relationship_types": relationship_types
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/graph/visualize")
def get_graph_visualization(
    mode: str = "all",
    labels: Optional[str] = None,
    relationships: Optional[str] = None,
    limit: int = 100
):
    """Get graph data for visualization with filtering options"""
    driver = get_driver()

    try:
        with driver.session() as session:
            # Build query based on mode
            if mode == "labels" and labels:
                label_list = [l.strip() for l in labels.split(",")]
                query = """
                MATCH (n)-[r]->(m)
                WHERE ANY(label IN labels(n) WHERE label IN $label_list)
                   OR ANY(label IN labels(m) WHERE label IN $label_list)
                WITH n, r, m
                LIMIT $limit
                RETURN n.id AS source_id, coalesce(n.name, n.id) AS source_name, labels(n) AS source_labels,
                       type(r) AS rel_type,
                       m.id AS target_id, coalesce(m.name, m.id) AS target_name, labels(m) AS target_labels
                """
                results = session.run(query, {"label_list": label_list, "limit": limit})

            elif mode == "relationships" and relationships:
                rel_types = [r.strip() for r in relationships.split(",")]
                query = """
                MATCH (n)-[r]->(m)
                WHERE type(r) IN $rel_types
                WITH n, r, m
                LIMIT $limit
                RETURN n.id AS source_id, coalesce(n.name, n.id) AS source_name, labels(n) AS source_labels,
                       type(r) AS rel_type,
                       m.id AS target_id, coalesce(m.name, m.id) AS target_name, labels(m) AS target_labels
                """
                results = session.run(query, {"rel_types": rel_types, "limit": limit})

            else:  # mode == "all"
                query = """
                MATCH (n)-[r]->(m)
                WITH n, r, m, rand() as random
                ORDER BY random
                LIMIT $limit
                RETURN n.id AS source_id, coalesce(n.name, n.id) AS source_name, labels(n) AS source_labels,
                       type(r) AS rel_type,
                       m.id AS target_id, coalesce(m.name, m.id) AS target_name, labels(m) AS target_labels
                """
                results = session.run(query, {"limit": limit})

            # Transform results to nodes and links format
            nodes_dict = {}
            links = []

            for record in results:
                source_id = record["source_id"]
                target_id = record["target_id"]

                # Add source node
                if source_id not in nodes_dict:
                    nodes_dict[source_id] = {
                        "id": source_id,
                        "name": record["source_name"],
                        "label": record["source_labels"][0] if record["source_labels"] else "Unknown"
                    }

                # Add target node
                if target_id not in nodes_dict:
                    nodes_dict[target_id] = {
                        "id": target_id,
                        "name": record["target_name"],
                        "label": record["target_labels"][0] if record["target_labels"] else "Unknown"
                    }

                # Add link
                links.append({
                    "source": source_id,
                    "target": target_id,
                    "type": record["rel_type"]
                })

            return {
                "nodes": list(nodes_dict.values()),
                "links": links
            }

    except Exception as e:
        return {"error": str(e)}
