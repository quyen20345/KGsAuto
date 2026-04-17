from __future__ import annotations

import json
from pathlib import Path

from ..config import RunConfig
from ..storage.entity_store_adapter import build_vector_store
from ..types import Stage1Result
from ..preprocessing.loader import extract_node_records, load_kg_files
from ..preprocessing.logger import setup_stage_logger
from ..preprocessing.normalize import build_embedding_text, normalize_properties, primary_type
from ..preprocessing.representation import create_embedding, get_embedding_model


def run_stage1(config: RunConfig) -> Stage1Result:
    # Setup logging
    logger = setup_stage_logger("stage1", config.stage_dir("stage1") / "stage1.log")
    logger.info(f"Starting Stage 1: run_id={config.run_id}")
    logger.info(f"Input directory: {config.input_dir}")

    # Load KG files
    kg_files = load_kg_files(config.input_dir)
    records = extract_node_records(kg_files)
    logger.info(f"Loaded {len(records)} node records from {len(kg_files)} files")

    # Detect embedding dimension (always use semantic with fallback to hash)
    embedding_method = "semantic"
    try:
        model = get_embedding_model(config.embedding_model)
        actual_dim = model.get_sentence_embedding_dimension()
        logger.info(f"Using semantic embedding: {config.embedding_model}, dimension={actual_dim}")
    except Exception as e:
        logger.error(f"Failed to load semantic model, falling back to hash: {e}")
        embedding_method = "hash"
        actual_dim = config.embedding_dim
        logger.info(f"Using hash embedding (fallback), dimension={actual_dim}")

    # Build vector store
    collection_name = config.resolve_collection_name()
    logger.info(f"Initializing vector store: backend={config.store_backend}, collection={collection_name}")

    store = build_vector_store(
        backend=config.store_backend,
        collection_name=collection_name,
        vector_dim=actual_dim,
        qdrant_url=config.qdrant_url,
    )

    # Create embeddings
    logger.info(f"Creating embeddings for {len(records)} records...")
    embedded_items: list[dict] = []

    for idx, rec in enumerate(records):
        if (idx + 1) % 100 == 0:
            logger.info(f"Progress: {idx + 1}/{len(records)} embeddings created")

        props = normalize_properties(rec.properties)
        text = build_embedding_text(rec.labels, props)

        # Create embedding using unified interface
        vector = create_embedding(
            text,
            method=embedding_method,
            model_name=config.embedding_model,
            dim=config.embedding_dim,
        )

        payload = {
            "run_id": config.run_id,
            "node_id": rec.node_id,
            "labels": rec.labels,
            "primary_type": primary_type(rec.labels),
            "source_file": rec.source_file,
            "chunk_id": props.get("chunk_id"),
            "embedding_text": text,
            "properties": props,
        }
        embedded_items.append({"node_id": rec.node_id, "vector": vector, "payload": payload})

    # Index embeddings
    logger.info(f"Indexing {len(embedded_items)} embeddings to vector store...")
    indexed = store.upsert_embeddings(embedded_items)
    logger.info(f"Successfully indexed {indexed} embeddings")

    # Save index metadata
    stage_dir = config.stage_dir("stage1")
    stage_dir.mkdir(parents=True, exist_ok=True)
    index_path = stage_dir / "index.json"

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "run_id": config.run_id,
                "collection_name": collection_name,
                "indexed_nodes": indexed,
                "embedding_method": embedding_method,
                "embedding_model": config.embedding_model if embedding_method == "semantic" else None,
                "embedding_dim": actual_dim,
                "nodes": [
                    {
                        "node_id": x["node_id"],
                        "primary_type": x["payload"]["primary_type"],
                        "source_file": x["payload"].get("source_file"),
                    }
                    for x in embedded_items
                ],
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    logger.info(f"Stage 1 completed successfully: {index_path}")

    return Stage1Result(
        run_id=config.run_id,
        collection_name=collection_name,
        indexed_nodes=indexed,
        index_path=str(index_path),
    )
