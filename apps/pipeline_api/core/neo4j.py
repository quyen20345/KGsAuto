from __future__ import annotations

from neo4j import GraphDatabase

from apps.pipeline_api.config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER


_driver = None


def get_neo4j_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return _driver


def close_neo4j_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
