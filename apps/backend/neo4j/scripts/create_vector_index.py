#!/usr/bin/env python3
"""
Create Neo4j vector index for entity embeddings.

This script creates a vector index on the embedding property
to enable fast similarity search.
"""
import os
import time
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")
INDEX_NAME = "entity_embedding_index"
VECTOR_DIM = 768


def create_vector_index():
    """Create vector index for entity embeddings."""
    print(f"Connecting to Neo4j at {NEO4J_URI}...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        with driver.session() as session:
            existing = session.run(
                """
                SHOW INDEXES
                YIELD name, type, labelsOrTypes, properties, state
                WHERE name = $index_name
                RETURN name, type, labelsOrTypes, properties, state
                LIMIT 1
                """,
                {"index_name": INDEX_NAME},
            ).single()

            if existing and (
                existing["type"] != "VECTOR"
                or existing["labelsOrTypes"] != ["VectorIndexed"]
                or existing["properties"] != ["embedding"]
            ):
                print(
                    f"Dropping existing index '{INDEX_NAME}' because it targets "
                    f"labels={existing['labelsOrTypes']} properties={existing['properties']}"
                )
                session.run(f"DROP INDEX {INDEX_NAME} IF EXISTS")
                existing = None

            if not existing:
                print(f"Creating vector index '{INDEX_NAME}'...")
                session.run(f"""
                    CREATE VECTOR INDEX {INDEX_NAME} IF NOT EXISTS
                    FOR (n:VectorIndexed)
                    ON (n.embedding)
                    OPTIONS {{
                      indexConfig: {{
                        `vector.dimensions`: {VECTOR_DIM},
                        `vector.similarity_function`: 'cosine'
                      }}
                    }}
                """)
                print("Vector index created successfully.")
            else:
                print(f"Index '{INDEX_NAME}' already exists with correct target.")

            time.sleep(2)

            print("\nCurrent indexes:")
            result = session.run("SHOW INDEXES")
            for record in result:
                index_name = record.get("name", "N/A")
                index_type = record.get("type", "N/A")
                state = record.get("state", "N/A")
                print(f"  - {index_name} ({index_type}): {state}")

            print(f"\nVector index '{INDEX_NAME}' is ready for use.")

    finally:
        driver.close()


if __name__ == "__main__":
    create_vector_index()
