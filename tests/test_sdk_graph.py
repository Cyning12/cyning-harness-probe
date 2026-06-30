"""SDK graph tests"""

from __future__ import annotations

from pathlib import Path

import pytest

from harness_probe.io import load_graph
from harness_sdk.graph import query_subgraph, subgraph_to_mermaid


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_load_graph():
    graph = load_graph(REPO_ROOT / "data" / "graph" / "sample_graph_v2.json")
    assert graph.freeze_id
    assert len(graph.nodes) > 0
    assert "RAG" in graph.node_map()


def test_subgraph_query():
    graph = load_graph(REPO_ROOT / "data" / "graph" / "sample_graph_v2.json")
    result = query_subgraph(graph, "RAG", depth=2)
    assert "RAG" in result.node_ids
    assert result.mermaid.startswith("flowchart TD")


def test_subgraph_query_missing_node():
    graph = load_graph(REPO_ROOT / "data" / "graph" / "sample_graph_v2.json")
    with pytest.raises(KeyError):
        query_subgraph(graph, "MISSING", depth=2)


def test_subgraph_to_mermaid():
    graph = load_graph(REPO_ROOT / "data" / "graph" / "sample_graph_v2.json")
    result = query_subgraph(graph, "RAG", depth=1)
    mermaid = subgraph_to_mermaid(graph.node_map(), result.edges, highlight="RAG")
    assert "RAG" in mermaid
    assert ":::entry" in mermaid
