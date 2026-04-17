"""
Debug script to analyze why UET nodes are not merging.

Tests:
1. Embedding similarity between 3 UET nodes
2. Stage 2 cluster assignments
3. Stage 3 LLM decisions
"""

import json
from pathlib import Path
from sentence_transformers import SentenceTransformer
import numpy as np


def load_mock_data():
    """Load 3 UET nodes from mock data."""
    mock_dir = Path("data/mock_data")
    target_ids = [
        "node_truong_dhcn",
        "node_truong_dai_hoc_cong_nghe",
        "node_truong_dai_hoc_cong_nghe_dhqghn",
    ]

    nodes = {}
    for json_file in mock_dir.glob("*.json"):
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            for node in data.get("nodes", []):
                if node["id"] in target_ids:
                    nodes[node["id"]] = node

    return nodes


def build_embedding_text(node):
    """Build embedding text using current pipeline logic."""
    props = node["properties"]
    name = props.get("name", "")
    aliases = props.get("aliases", [])

    if aliases:
        name_lower = name.lower().strip()
        filtered_aliases = [
            alias for alias in aliases
            if alias and alias.lower().strip() != name_lower
        ]

        if filtered_aliases:
            sorted_aliases = sorted(filtered_aliases, key=len, reverse=True)
            aliases_part = ", ".join(sorted_aliases)
            return f"{name} || {aliases_part}"

    return name


def compute_embeddings(nodes, model_name):
    """Compute embeddings for nodes."""
    print(f"\n{'='*80}")
    print(f"Loading model: {model_name}")
    model = SentenceTransformer(model_name)
    print(f"Model dimension: {model.get_sentence_embedding_dimension()}")

    embeddings = {}
    texts = {}

    for node_id, node in nodes.items():
        text = build_embedding_text(node)
        texts[node_id] = text
        embeddings[node_id] = model.encode(text)
        print(f"\n{node_id}:")
        print(f"  Text: {text}")

    return embeddings, texts


def compute_similarities(embeddings):
    """Compute pairwise cosine similarities."""
    print(f"\n{'='*80}")
    print("PAIRWISE COSINE SIMILARITIES:")

    node_ids = list(embeddings.keys())
    for i, id1 in enumerate(node_ids):
        for id2 in node_ids[i+1:]:
            vec1 = embeddings[id1]
            vec2 = embeddings[id2]

            # Cosine similarity
            similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

            print(f"\n{id1}")
            print(f"  vs {id2}")
            print(f"  Similarity: {similarity:.4f}")


def check_stage2_clusters(run_id):
    """Check Stage 2 cluster assignments."""
    print(f"\n{'='*80}")
    print("STAGE 2 CLUSTER ASSIGNMENTS:")

    assignments_path = Path(f"entity_resolution/artifacts/{run_id}/stage2/cluster_assignments.json")

    if not assignments_path.exists():
        print(f"  File not found: {assignments_path}")
        return

    with open(assignments_path, "r", encoding="utf-8") as f:
        assignments = json.load(f)

    target_ids = [
        "node_truong_dhcn",
        "node_truong_dai_hoc_cong_nghe",
        "node_truong_dai_hoc_cong_nghe_dhqghn",
    ]

    for assignment in assignments:
        if assignment["node_id"] in target_ids:
            print(f"\n{assignment['node_id']}:")
            print(f"  Cluster: {assignment['cluster_id']}")
            print(f"  Probability: {assignment['probability']}")
            print(f"  Primary type: {assignment['primary_type']}")


def check_stage3_remap(run_id):
    """Check Stage 3 ID remap."""
    print(f"\n{'='*80}")
    print("STAGE 3 ID REMAP:")

    remap_path = Path(f"entity_resolution/artifacts/{run_id}/stage3/id_remap.json")

    if not remap_path.exists():
        print(f"  File not found: {remap_path}")
        return

    with open(remap_path, "r", encoding="utf-8") as f:
        remap = json.load(f)

    target_ids = [
        "node_truong_dhcn",
        "node_truong_dai_hoc_cong_nghe",
        "node_truong_dai_hoc_cong_nghe_dhqghn",
    ]

    for node_id in target_ids:
        canonical = remap.get(node_id, node_id)
        print(f"\n{node_id} → {canonical}")


def main():
    print("="*80)
    print("UET NODES MERGE DEBUG")
    print("="*80)

    # Load nodes
    nodes = load_mock_data()
    print(f"\nLoaded {len(nodes)} nodes:")
    for node_id in nodes:
        print(f"  - {node_id}")

    # Test with all models
    for model_name in [
        "paraphrase-multilingual-mpnet-base-v2",
        "AITeamVN/Vietnamese_Embedding",
        "dangvantuan/vietnamese-embedding",
    ]:
        embeddings, texts = compute_embeddings(nodes, model_name)
        compute_similarities(embeddings)

    # Check pipeline results
    run_id = "experiment_vietnamese_aliases_065"
    check_stage2_clusters(run_id)
    check_stage3_remap(run_id)

    print(f"\n{'='*80}")
    print("ANALYSIS COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
