"""graph_v2 加载与子图查询（L0）"""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path

from src.models import GraphEdge, GraphNode, SubgraphResult, TechGraph


def load_graph(path: str | Path) -> TechGraph:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    nodes = [GraphNode.model_validate(n) for n in raw.get("nodes", [])]
    edges = [GraphEdge.model_validate(e) for e in raw.get("edges", [])]
    return TechGraph(
        schema_version=raw.get("schema_version", "graph_v2"),
        freeze_id=raw.get("freeze_id", "UNKNOWN"),
        generated_at=raw.get("generated_at"),
        nodes=nodes,
        edges=edges,
    )


def _adjacency(edges: list[GraphEdge]) -> dict[str, list[tuple[str, GraphEdge]]]:
    adj: dict[str, list[tuple[str, GraphEdge]]] = {}
    for edge in edges:
        adj.setdefault(edge.from_id, []).append((edge.to_id, edge))
        adj.setdefault(edge.to_id, []).append((edge.from_id, edge))
    return adj


def query_subgraph(
    graph: TechGraph,
    entry_node_id: str,
    depth: int = 2,
    direction: str = "both",
) -> SubgraphResult:
    """BFS 裁剪子图 · 模拟 tech_graph_graph_query neighbors"""
    node_map = graph.node_map()
    if entry_node_id not in node_map:
        raise KeyError(f"node not found: {entry_node_id}")

    adj = _adjacency(graph.edges)
    seen: set[str] = {entry_node_id}
    queue: deque[tuple[str, int]] = deque([(entry_node_id, 0)])

    while queue:
        current, d = queue.popleft()
        if d >= depth:
            continue
        for neighbor, _edge in adj.get(current, []):
            if neighbor in seen:
                continue
            seen.add(neighbor)
            queue.append((neighbor, d + 1))

    sub_edges = [
        e
        for e in graph.edges
        if e.from_id in seen and e.to_id in seen
    ]
    mermaid = subgraph_to_mermaid(node_map, sub_edges, entry_node_id)
    return SubgraphResult(
        entry_node=entry_node_id,
        depth=depth,
        node_ids=sorted(seen),
        edges=sub_edges,
        mermaid=mermaid,
    )


def subgraph_to_mermaid(
    node_map: dict[str, GraphNode],
    edges: list[GraphEdge],
    highlight: str | None = None,
) -> str:
    lines = ["flowchart TD"]
    for nid in sorted(node_map.keys()):
        if nid not in {e.from_id for e in edges} | {e.to_id for e in edges}:
            continue
        label = node_map[nid].label.replace('"', "'")
        if nid == highlight:
            lines.append(f'    {nid}["{label}"]:::entry')
        else:
            lines.append(f'    {nid}["{label}"]')
    for edge in edges:
        mark = edge.mark or "->"
        lines.append(f"    {edge.from_id} --\"{mark}\"--> {edge.to_id}")
        for anchor in edge.anchors[:2]:
            sym = anchor.symbol or anchor.path
            lines.append(f"    %% → {anchor.path}::{sym}")
    lines.append("    classDef entry fill:#eef,stroke:#336")
    return "\n".join(lines)
