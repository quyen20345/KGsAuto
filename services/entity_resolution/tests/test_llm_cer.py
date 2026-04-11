"""
Unit tests for LLM-CER components
"""

import numpy as np
import pytest


class TestRecordSetBuilder:
    """Tests for RecordSetBuilder (NRS algorithm)"""

    def test_small_cluster_single_set(self):
        """Small cluster (≤9 entities) should return single set"""
        from services.entity_resolution.blocking.record_set_builder import RecordSetBuilder

        builder = RecordSetBuilder(optimal_set_size=9)

        # 5 entities
        cluster_items = [{"node_id": f"node_{i}"} for i in range(5)]
        embeddings = {f"node_{i}": [0.1 * i] * 10 for i in range(5)}

        record_sets = builder.build_record_sets(cluster_items, embeddings)

        assert len(record_sets) == 1
        assert len(record_sets[0]) == 5

    def test_large_cluster_multiple_sets(self):
        """Large cluster (>9 entities) should be split into multiple sets"""
        from services.entity_resolution.blocking.record_set_builder import RecordSetBuilder

        builder = RecordSetBuilder(optimal_set_size=9)

        # 20 entities
        cluster_items = [{"node_id": f"node_{i}"} for i in range(20)]
        embeddings = {f"node_{i}": [0.1 * i] * 10 for i in range(20)}

        record_sets = builder.build_record_sets(cluster_items, embeddings)

        # Should create 2-3 sets
        assert 2 <= len(record_sets) <= 3

        # Each set should be reasonably sized
        for record_set in record_sets:
            assert 5 <= len(record_set) <= 12

        # All entities should be included
        all_nodes = []
        for record_set in record_sets:
            all_nodes.extend([item["node_id"] for item in record_set])
        assert len(all_nodes) == 20
        assert len(set(all_nodes)) == 20  # No duplicates


class TestMDGValidator:
    """Tests for MDGValidator"""

    def test_valid_clustering_high_intra_low_inter(self):
        """Valid clustering: high intra-cluster, low inter-cluster similarity"""
        from services.entity_resolution.evaluation.mdg_validator import MDGValidator

        validator = MDGValidator(similarity_threshold=0.1)

        # Create embeddings: two distinct groups
        embeddings = {
            "e1": [1.0, 0.0, 0.0],
            "e2": [0.9, 0.1, 0.0],  # Similar to e1
            "e3": [0.0, 0.0, 1.0],
            "e4": [0.0, 0.1, 0.9],  # Similar to e3
        }

        # Good clustering: e1+e2 in one group, e3+e4 in another
        clustering_result = {
            "groups": [
                {"group_id": "g0", "node_ids": ["e1", "e2"]},
                {"group_id": "g1", "node_ids": ["e3", "e4"]},
            ]
        }

        is_valid, reason = validator.validate_clustering(clustering_result, embeddings)
        assert is_valid

    def test_invalid_clustering_low_intra_high_inter(self):
        """Invalid clustering: low intra-cluster, high inter-cluster similarity"""
        from services.entity_resolution.evaluation.mdg_validator import MDGValidator

        validator = MDGValidator(similarity_threshold=0.1)

        # Create embeddings: two distinct groups
        embeddings = {
            "e1": [1.0, 0.0, 0.0],
            "e2": [0.9, 0.1, 0.0],  # Similar to e1
            "e3": [0.0, 0.0, 1.0],
            "e4": [0.0, 0.1, 0.9],  # Similar to e3
        }

        # Bad clustering: e1+e3 in one group (dissimilar), e2+e4 in another (dissimilar)
        clustering_result = {
            "groups": [
                {"group_id": "g0", "node_ids": ["e1", "e3"]},
                {"group_id": "g1", "node_ids": ["e2", "e4"]},
            ]
        }

        is_valid, reason = validator.validate_clustering(clustering_result, embeddings)
        assert not is_valid

    def test_single_group_always_valid(self):
        """Single group should always be valid"""
        from services.entity_resolution.evaluation.mdg_validator import MDGValidator

        validator = MDGValidator(similarity_threshold=0.1)

        embeddings = {
            "e1": [1.0, 0.0, 0.0],
            "e2": [0.0, 1.0, 0.0],
        }

        clustering_result = {
            "groups": [
                {"group_id": "g0", "node_ids": ["e1", "e2"]},
            ]
        }

        is_valid, reason = validator.validate_clustering(clustering_result, embeddings)
        assert is_valid


class TestHierarchicalClusterMerger:
    """Tests for HierarchicalClusterMerger (CMR algorithm)"""

    def test_single_round_no_merge(self):
        """Single round should return groups as-is"""
        from services.entity_resolution.clustering.cluster_merger import HierarchicalClusterMerger

        merger = HierarchicalClusterMerger(merge_threshold=0.80)

        embeddings = {
            "e1": [1.0, 0.0],
            "e2": [0.9, 0.1],
        }

        round_results = [
            {
                "groups": [
                    {"group_id": "g0", "node_ids": ["e1", "e2"]},
                ]
            }
        ]

        merged = merger.merge_clusters(round_results, embeddings)
        assert len(merged) == 1
        assert set(merged[0]["node_ids"]) == {"e1", "e2"}

    def test_merge_similar_groups_across_rounds(self):
        """Similar groups across rounds should be merged"""
        from services.entity_resolution.clustering.cluster_merger import HierarchicalClusterMerger

        merger = HierarchicalClusterMerger(merge_threshold=0.80)

        # Create similar embeddings
        embeddings = {
            "e1": [1.0, 0.0, 0.0],
            "e2": [0.9, 0.1, 0.0],
            "e3": [0.95, 0.05, 0.0],
            "e4": [0.0, 0.0, 1.0],
        }

        # Two rounds with similar groups
        round_results = [
            {
                "groups": [
                    {"group_id": "g0", "node_ids": ["e1", "e2"]},
                    {"group_id": "g1", "node_ids": ["e4"]},
                ]
            },
            {
                "groups": [
                    {"group_id": "g0", "node_ids": ["e3"]},  # Similar to e1, e2
                ]
            },
        ]

        merged = merger.merge_clusters(round_results, embeddings)

        # Should merge e1, e2, e3 into one group
        # e4 should be separate
        assert len(merged) == 2

        # Find the large group
        large_group = max(merged, key=lambda g: len(g["node_ids"]))
        assert set(large_group["node_ids"]) == {"e1", "e2", "e3"}


class TestLLMClusterer:
    """Tests for LLMClusterer"""

    def test_extract_json_from_markdown(self):
        """Should extract JSON from markdown code blocks"""
        from services.entity_resolution.matching.llm_cer import LLMClusterer

        clusterer = LLMClusterer("proxypal", "gpt-5")

        response = '''```json
{
  "groups": [
    {"group_id": "g0", "node_ids": ["e1", "e2"]}
  ],
  "confidence": 0.9
}
```'''

        result = clusterer._extract_json(response)
        assert result is not None
        assert "groups" in result
        assert result["confidence"] == 0.9

    def test_extract_json_plain(self):
        """Should extract plain JSON"""
        from services.entity_resolution.matching.llm_cer import LLMClusterer

        clusterer = LLMClusterer("proxypal", "gpt-5")

        response = '{"groups": [{"group_id": "g0", "node_ids": ["e1"]}], "confidence": 0.8}'

        result = clusterer._extract_json(response)
        assert result is not None
        assert "groups" in result
        assert result["confidence"] == 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
