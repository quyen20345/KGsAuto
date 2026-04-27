"""Neo4j graph storage adapter"""

from typing import List, Dict, Any, Optional

from apps.backend.app.db.neo4j import get_driver


class GraphStore:
    """Query knowledge graph in Neo4j"""

    def __init__(self, config):
        self.config = config
        self.driver = get_driver()

    def search_entities(self, name_fragment: str, limit: int = 10) -> List[Dict[str, Any]]:
        query = """
        MATCH (n)
        WHERE n.id IS NOT NULL
          AND n.name IS NOT NULL
          AND (
            toLower(n.name) CONTAINS toLower($fragment)
            OR any(alias IN coalesce(n.aliases, []) WHERE toLower(alias) CONTAINS toLower($fragment))
          )
        RETURN n.id as id, n.name as name, labels(n) as labels,
               n.chunk_id as chunk_ids
        ORDER BY size(n.name) ASC
        LIMIT $limit
        """

        with self.driver.session() as session:
            results = session.run(query, {"fragment": name_fragment, "limit": limit})
            return [record.data() for record in results]

    def get_entity_details(self, entity_id: str) -> Optional[Dict[str, Any]]:
        query = """
        MATCH (n {id: $entity_id})
        RETURN n.id as id, n.name as name, labels(n) as labels,
               properties(n) as properties
        """

        with self.driver.session() as session:
            result = session.run(query, {"entity_id": entity_id})
            record = result.single()
            return record.data() if record else None

    def get_relationships(self, entity_id: str, depth: int = 1, limit: int = 20) -> List[Dict[str, Any]]:
        if depth == 1:
            query = """
            MATCH (n {id: $entity_id})-[r]-(m)
            WHERE m.id IS NOT NULL
            RETURN n.name as source, type(r) as relation, m.name as target,
                   m.id as target_id, properties(r) as rel_props
            LIMIT $limit
            """
        else:
            query = """
            MATCH path = (n {id: $entity_id})-[*1..2]-(m)
            WHERE m.id <> $entity_id AND m.id IS NOT NULL
            RETURN [node in nodes(path) | node.name] as path_names,
                   [rel in relationships(path) | type(rel)] as rel_types
            LIMIT $limit
            """

        with self.driver.session() as session:
            results = session.run(query, {"entity_id": entity_id, "limit": limit})
            return [record.data() for record in results]

    def execute_query(self, cypher: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        with self.driver.session() as session:
            results = session.run(cypher, params or {})
            return [record.data() for record in results]

    def test_connection(self) -> bool:
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                return result.single()["test"] == 1
        except Exception as e:
            print(f"✗ Neo4j connection failed: {e}")
            return False

    def get_entity_count(self) -> int:
        query = "MATCH (n) WHERE n.id IS NOT NULL RETURN count(n) as count"
        with self.driver.session() as session:
            result = session.run(query)
            return result.single()["count"]
