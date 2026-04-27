#!/usr/bin/env python3
"""
Add embeddings to all nodes in Neo4j graph.

This script:
1. Reads all nodes from Neo4j
2. Generates embeddings using paraphrase-multilingual-mpnet-base-v2
3. Updates each node with embedding property (768-dim vector)
4. Uses same embedding text format as entity resolution
"""
import os
import sys
import time
from pathlib import Path
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from services.entity_resolution.preprocessing.representation import (
    get_embedding_model,
    semantic_embedding,
)
from services.entity_resolution.preprocessing.normalize import build_embedding_text

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")
MODEL_NAME = "paraphrase-multilingual-mpnet-base-v2"
BATCH_SIZE = 100


def add_embeddings_to_nodes():
    """Add embeddings to all nodes in Neo4j."""
    print(f"Connecting to Neo4j at {NEO4J_URI}...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        # Load and cache embedding model
        print(f"Loading embedding model: {MODEL_NAME}...")
        get_embedding_model(MODEL_NAME)
        print("Model loaded successfully.")

        # Count total nodes
        with driver.session() as session:
            result = session.run("MATCH (n) WHERE n.id IS NOT NULL RETURN count(n) AS total")
            total_nodes = result.single()["total"]
            print(f"Found {total_nodes} nodes to process.")

        if total_nodes == 0:
            print("No nodes found. Exiting.")
            return

        # Process nodes in batches
        processed = 0
        start_time = time.time()

        with driver.session() as session:
            # Fetch all nodes
            result = session.run("""
                MATCH (n)
                WHERE n.id IS NOT NULL
                RETURN n.id AS id, labels(n) AS labels, properties(n) AS properties
            """)

            batch = []
            for record in result:
                node_id = record["id"]
                labels = record["labels"]
                properties = record["properties"]

                # Build embedding text
                embedding_text = build_embedding_text(labels, properties)

                # Generate embedding
                embedding = semantic_embedding(embedding_text, MODEL_NAME)

                batch.append({"id": node_id, "embedding": embedding})

                # Update in batches
                if len(batch) >= BATCH_SIZE:
                    _update_batch(session, batch)
                    processed += len(batch)
                    elapsed = time.time() - start_time
                    rate = processed / elapsed if elapsed > 0 else 0
                    print(f"Processed {processed}/{total_nodes} nodes ({rate:.1f} nodes/sec)")
                    batch = []

            # Update remaining batch
            if batch:
                _update_batch(session, batch)
                processed += len(batch)

        elapsed = time.time() - start_time
        print(f"\nCompleted! Added embeddings to {processed} nodes in {elapsed:.1f} seconds.")
        print(f"Average rate: {processed/elapsed:.1f} nodes/sec")

    finally:
        driver.close()


def _update_batch(session, batch):
    """Update a batch of nodes with embeddings."""
    for item in batch:
        session.run(
            "MATCH (n {id: $id}) SET n:VectorIndexed, n.embedding = $embedding",
            id=item["id"],
            embedding=item["embedding"]
        )


if __name__ == "__main__":
    add_embeddings_to_nodes()
