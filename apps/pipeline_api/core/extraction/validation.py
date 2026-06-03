"""Validation utilities for extracted knowledge graphs"""

from typing import Dict, Any, List, Tuple


def validate_kg_structure(kg_data: Dict[str, Any], chunk_id: str) -> Tuple[bool, List[str]]:
    """
    Validate knowledge graph structure and return validation result.

    Args:
        kg_data: Extracted knowledge graph data
        chunk_id: Document identifier for error messages

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Check required keys
    if "nodes" not in kg_data:
        errors.append("Missing 'nodes' key")
    if "relationships" not in kg_data:
        errors.append("Missing 'relationships' key")

    if errors:
        return False, errors

    nodes = kg_data["nodes"]
    relationships = kg_data["relationships"]

    # Check for empty results
    if len(nodes) == 0:
        errors.append("No nodes extracted - empty graph")

    # Validate nodes
    node_ids = []
    for idx, node in enumerate(nodes):
        node_id = node.get("id")
        if not node_id:
            errors.append(f"Node at index {idx} missing 'id' field")
            continue

        node_ids.append(node_id)

        # Check labels
        labels = node.get("labels")
        if not labels:
            errors.append(f"Node '{node_id}' missing 'labels' field")
        elif not isinstance(labels, list):
            errors.append(f"Node '{node_id}' labels must be an array")
        elif len(labels) == 0:
            errors.append(f"Node '{node_id}' has empty labels array")

        # Check properties
        properties = node.get("properties")
        if not properties:
            errors.append(f"Node '{node_id}' missing 'properties' field")
        elif not isinstance(properties, dict):
            errors.append(f"Node '{node_id}' properties must be an object")
        else:
            # Check required properties
            if "chunk_id" not in properties:
                errors.append(f"Node '{node_id}' missing required property 'chunk_id'")
            if "model_extracted" not in properties:
                errors.append(f"Node '{node_id}' missing required property 'model_extracted'")

    # Check node ID uniqueness
    if node_ids:
        duplicates = [nid for nid in set(node_ids) if node_ids.count(nid) > 1]
        if duplicates:
            errors.append(f"Duplicate node IDs found: {duplicates}")

    # Validate relationships
    node_id_set = set(node_ids)
    for idx, rel in enumerate(relationships):
        rel_id = rel.get("id", f"relationship_{idx}")

        # Check type
        rel_type = rel.get("type")
        if not rel_type:
            errors.append(f"Relationship '{rel_id}' missing 'type' field")

        # Check source and target
        source = rel.get("source")
        target = rel.get("target")

        if not source:
            errors.append(f"Relationship '{rel_id}' missing 'source' field")
        elif source not in node_id_set:
            errors.append(f"Relationship '{rel_id}' has orphaned source: '{source}' not in nodes")

        if not target:
            errors.append(f"Relationship '{rel_id}' missing 'target' field")
        elif target not in node_id_set:
            errors.append(f"Relationship '{rel_id}' has orphaned target: '{target}' not in nodes")

        # Check properties
        properties = rel.get("properties")
        if properties and isinstance(properties, dict):
            if "chunk_id" not in properties:
                errors.append(f"Relationship '{rel_id}' missing required property 'chunk_id'")
            if "model_extracted" not in properties:
                errors.append(f"Relationship '{rel_id}' missing required property 'model_extracted'")

    return len(errors) == 0, errors


def validate_and_log(kg_data: Dict[str, Any], chunk_id: str, logger) -> bool:
    """
    Validate KG structure and log errors if any.

    Args:
        kg_data: Extracted knowledge graph data
        chunk_id: Document identifier
        logger: Logger instance

    Returns:
        True if valid, False otherwise
    """
    is_valid, errors = validate_kg_structure(kg_data, chunk_id)

    if not is_valid:
        logger.warning(f"Validation failed for {chunk_id}:")
        for error in errors:
            logger.warning(f"  - {error}")

    return is_valid
