"""Harness Probe tests"""

from src.compiler import compile_contracts_from_task, parse_task_markdown
from src.graph_loader import load_graph, query_subgraph


SAMPLE_TASK = """
## 失败路径
| 触发条件 | 系统行为 | 可重试 | 用户可见 |
| hits == 0 | fallback | 否 | no_data |
"""


def test_compile_contracts():
    contracts = compile_contracts_from_task(SAMPLE_TASK)
    assert len(contracts) == 1
    assert contracts[0].ref == "F1"
    assert "hits" in contracts[0].trigger


def test_subgraph_query():
    graph = load_graph("data/graph/sample_graph_v2.json")
    result = query_subgraph(graph, "RAG", depth=2)
    assert "RAG" in result.node_ids
    assert "HIT0" in result.node_ids or "FTS" in result.node_ids


def test_parse_sample_task():
    task = parse_task_markdown("data/tasks/sample_task.md")
    assert task.entry_node == "RAG"
    assert len(task.contracts) >= 2
    assert task.is_gate_approved("HG-AUDIT-R1")
