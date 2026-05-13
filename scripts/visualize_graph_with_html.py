from collections import Counter
from pathlib import Path
import json
import random

import pipmaster as pm

if not pm.is_installed("pyvis"):
    pm.install("pyvis")

from pyvis.network import Network

BASE_DIR = Path(__file__).resolve().parent
# GRAPH_DIR = BASE_DIR / "data" / "extracted"
GRAPH_DIR = BASE_DIR / "data" / "entity_resolution" / "artifacts" / "test_canonical_name_realdata" / "stage3" / "output_graph"
OUTPUT_HTML = BASE_DIR / "knowledge_graph_extracted.html"
MAX_NODES = 1500
MAX_EDGES = 3000


LABEL_COLORS = {
    "PERSON": "#60a5fa",
    "UNIVERSITY": "#f59e0b",
    "FACULTY": "#34d399",
    "DEPARTMENT": "#22c55e",
    "INSTITUTE": "#a78bfa",
    "LAB": "#f472b6",
    "PROGRAM": "#f97316",
    "COURSE": "#fb7185",
    "EVENT": "#06b6d4",
    "DOCUMENT": "#94a3b8",
    "PUBLICATION": "#c084fc",
    "SCHOLARSHIP": "#eab308",
    "PARTNERSHIP": "#14b8a6",
    "LOCATION": "#84cc16",
    "BUILDING": "#10b981",
    "ROOM": "#8b5cf6",
    "WEBSITE": "#3b82f6",
    "SYSTEM": "#0ea5e9",
}


def load_graph_fragments(graph_dir: Path) -> tuple[dict[str, dict], list[dict], dict[str, int]]:
    if not graph_dir.exists():
        raise FileNotFoundError(f"Graph directory not found: {graph_dir}")

    files = sorted(graph_dir.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"No JSON graph files found in: {graph_dir}")

    nodes: dict[str, dict] = {}
    relationships: dict[str, dict] = {}

    for file_path in files:
        with open(file_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        for node in payload.get("nodes", []):
            node_id = node.get("id")
            if node_id and node_id not in nodes:
                nodes[node_id] = node

        for relationship in payload.get("relationships", []):
            rel_id = relationship.get("id")
            if rel_id:
                relationships[rel_id] = relationship

    stats = {
        "files": len(files),
        "nodes": len(nodes),
        "relationships": len(relationships),
    }
    return nodes, list(relationships.values()), stats


def select_subgraph(nodes: dict[str, dict], relationships: list[dict]) -> tuple[dict[str, dict], list[dict], bool]:
    if len(nodes) <= MAX_NODES and len(relationships) <= MAX_EDGES:
        return nodes, relationships, False

    degree = Counter()
    for relationship in relationships:
        source = relationship.get("source")
        target = relationship.get("target")
        if source:
            degree[source] += 1
        if target:
            degree[target] += 1

    selected_node_ids = {
        node_id
        for node_id, _ in degree.most_common(MAX_NODES)
        if node_id in nodes
    }

    if len(selected_node_ids) < min(MAX_NODES, len(nodes)):
        for node_id in nodes:
            selected_node_ids.add(node_id)
            if len(selected_node_ids) >= min(MAX_NODES, len(nodes)):
                break

    filtered_relationships = []
    for relationship in relationships:
        source = relationship.get("source")
        target = relationship.get("target")
        if source in selected_node_ids and target in selected_node_ids:
            filtered_relationships.append(relationship)
        if len(filtered_relationships) >= MAX_EDGES:
            break

    filtered_nodes = {node_id: nodes[node_id] for node_id in selected_node_ids}
    return filtered_nodes, filtered_relationships, True


def get_node_label(node: dict) -> str:
    labels = node.get("labels") or []
    return labels[0] if labels else "ENTITY"


def get_node_name(node: dict) -> str:
    properties = node.get("properties") or {}
    return properties.get("name") or node.get("id") or "Unknown"


def get_node_title(node: dict) -> str:
    properties = node.get("properties") or {}
    aliases = properties.get("aliases") or []
    chunk_id = properties.get("chunk_id")
    description = properties.get("description") or ""
    lines = [
        f"id: {node.get('id', '')}",
        f"label: {get_node_label(node)}",
        f"name: {get_node_name(node)}",
    ]
    if aliases:
        lines.append(f"aliases: {', '.join(aliases)}")
    if chunk_id:
        lines.append(f"chunk_id: {chunk_id}")
    if description:
        lines.append(f"description: {description}")
    return "<br>".join(lines)


def get_edge_title(relationship: dict) -> str:
    properties = relationship.get("properties") or {}
    description = properties.get("description") or ""
    chunk_id = properties.get("chunk_id")
    lines = [
        f"id: {relationship.get('id', '')}",
        f"type: {relationship.get('type', '')}",
        f"source: {relationship.get('source', '')}",
        f"target: {relationship.get('target', '')}",
    ]
    if chunk_id:
        lines.append(f"chunk_id: {chunk_id}")
    if description:
        lines.append(f"description: {description}")
    return "<br>".join(lines)


def build_network(nodes: dict[str, dict], relationships: list[dict], stats: dict[str, int], truncated: bool) -> Network:
    net = Network(height="100vh", width="100%", bgcolor="#111827", font_color="#e5e7eb", directed=True)
    net.barnes_hut(gravity=-30000, central_gravity=0.15, spring_length=150, spring_strength=0.04, damping=0.85)
    net.toggle_physics(True)

    for node_id, node in nodes.items():
        label = get_node_label(node)
        name = get_node_name(node)
        color = LABEL_COLORS.get(label, "#{:06x}".format(random.randint(0, 0xFFFFFF)))
        degree_hint = 1
        net.add_node(
            node_id,
            label=name,
            title=get_node_title(node),
            color=color,
            group=label,
            shape="dot",
            size=10 + degree_hint,
        )

    for relationship in relationships:
        source = relationship.get("source")
        target = relationship.get("target")
        if source not in nodes or target not in nodes:
            continue
        rel_type = relationship.get("type") or "RELATED_TO"
        net.add_edge(
            source,
            target,
            label=rel_type,
            title=get_edge_title(relationship),
            color="#9ca3af",
            arrows="to",
        )

    subtitle = (
        f"files={stats['files']} | nodes={stats['nodes']} | relationships={stats['relationships']}"
        + (" | truncated for visualization" if truncated else "")
    )
    net.heading = f"Extracted Graph<br><span style='font-size:16px'>{subtitle}</span>"
    return net


def main() -> None:
    nodes, relationships, stats = load_graph_fragments(GRAPH_DIR)
    selected_nodes, selected_relationships, truncated = select_subgraph(nodes, relationships)
    net = build_network(selected_nodes, selected_relationships, stats, truncated)
    net.show(str(OUTPUT_HTML), notebook=False)
    print(f"Graph HTML written to: {OUTPUT_HTML}")
    print(
        "Visualized "
        f"{len(selected_nodes)} nodes and {len(selected_relationships)} relationships "
        f"from {stats['files']} files."
    )


if __name__ == "__main__":
    main()
