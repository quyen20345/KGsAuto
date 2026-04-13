"""
Unit tests for MDG Validator.

Tests the Misclustering Detection Guardrail (MDG) validation logic.
"""

from __future__ import annotations

import pytest

from services.entity_resolution.evaluation.mdg_validator import MDGValidator


def test_mdg_rejects_all_singleton_for_multi_entity_input():
    """MDG should reject all-singleton when input has multiple entities."""
    validator = MDGValidator()

    # Simulate LLM output: 3 entities, all in separate groups
    clustering_result = {
        "groups": [
            {"group_id": "g0", "node_ids": ["node_1"]},
            {"group_id": "g1", "node_ids": ["node_2"]},
            {"group_id": "g2", "node_ids": ["node_3"]},
        ]
    }

    embeddings = {
        "node_1": [0.1] * 64,
        "node_2": [0.2] * 64,
        "node_3": [0.3] * 64,
    }

    is_valid, reason = validator.validate_clustering(clustering_result, embeddings)

    assert is_valid is False
    assert "suspicious" in reason.lower()
    assert "3 entities" in reason


def test_mdg_passes_legitimate_singleton():
    """MDG should pass when input truly has only 1 entity."""
    validator = MDGValidator()

    clustering_result = {
        "groups": [
            {"group_id": "g0", "node_ids": ["node_1"]},
        ]
    }

    embeddings = {"node_1": [0.1] * 64}

    is_valid, reason = validator.validate_clustering(clustering_result, embeddings)

    assert is_valid is True
    # Single group is handled by the "Single or empty cluster" path
    assert "single" in reason.lower() or "empty" in reason.lower()


def test_mdg_passes_valid_multi_node_groups():
    """MDG should pass when groups have multiple nodes with good clustering."""
    validator = MDGValidator()

    # Two groups with high intra-cluster similarity
    clustering_result = {
        "groups": [
            {"group_id": "g0", "node_ids": ["node_1", "node_2"]},
            {"group_id": "g1", "node_ids": ["node_3", "node_4"]},
        ]
    }

    # High similarity within groups, low between groups
    embeddings = {
        "node_1": [0.9, 0.1] + [0.0] * 62,
        "node_2": [0.91, 0.09] + [0.0] * 62,  # Similar to node_1
        "node_3": [0.1, 0.9] + [0.0] * 62,
        "node_4": [0.09, 0.91] + [0.0] * 62,  # Similar to node_3
    }

    is_valid, reason = validator.validate_clustering(clustering_result, embeddings)

    assert is_valid is True
    assert "passed" in reason.lower()


def test_mdg_rejects_bad_clustering():
    """MDG should reject when inter-cluster similarity is too high."""
    validator = MDGValidator(similarity_threshold=0.1)

    # Two groups but entities are actually similar (bad clustering)
    clustering_result = {
        "groups": [
            {"group_id": "g0", "node_ids": ["node_1", "node_2"]},
            {"group_id": "g1", "node_ids": ["node_3", "node_4"]},
        ]
    }

    # All entities are similar (should be in same group)
    embeddings = {
        "node_1": [0.9] * 64,
        "node_2": [0.91] * 64,
        "node_3": [0.89] * 64,
        "node_4": [0.92] * 64,
    }

    is_valid, reason = validator.validate_clustering(clustering_result, embeddings)

    assert is_valid is False
    assert "failed" in reason.lower()


def test_mdg_handles_empty_groups():
    """MDG should handle empty groups gracefully."""
    validator = MDGValidator()

    clustering_result = {"groups": []}
    embeddings = {}

    is_valid, reason = validator.validate_clustering(clustering_result, embeddings)

    # Empty is treated as single/empty cluster
    assert is_valid is True


def test_mdg_handles_mixed_singleton_and_multi_node():
    """MDG should validate mixed groups (some singleton, some multi-node)."""
    validator = MDGValidator()

    clustering_result = {
        "groups": [
            {"group_id": "g0", "node_ids": ["node_1", "node_2"]},  # Multi-node
            {"group_id": "g1", "node_ids": ["node_3"]},  # Singleton
        ]
    }

    # Good clustering: node_1 and node_2 are similar, node_3 is different
    embeddings = {
        "node_1": [0.9, 0.1] + [0.0] * 62,
        "node_2": [0.91, 0.09] + [0.0] * 62,
        "node_3": [0.1, 0.9] + [0.0] * 62,
    }

    is_valid, reason = validator.validate_clustering(clustering_result, embeddings)

    # Should pass because there's at least one multi-node group with good clustering
    assert is_valid is True
