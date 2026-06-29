"""Harness Probe tests"""

from src.builder import build_hat_prompt
from src.compiler import (
    compile_contracts_from_task,
    parse_task_markdown,
    validate_human_gate_rules,
    validate_task_markdown,
)
from src.graph_loader import load_graph, query_subgraph
from src.models import HumanGate


SAMPLE_TASK = """
## 失败路径
| 触发条件 | 系统行为 | 可重试 | 用户可见 |
| hits == 0 | fallback | 否 | no_data |
"""

TASK_NO_HG = """
## Harness 元信息
| 字段 | 值 |
| **test_strategy** | `recommended` |

## 失败路径
| 触发条件 | 系统行为 | 可重试 | 用户可见 |
| hits == 0 | fallback | 否 | no_data |
"""

TASK_HG_NO_AUDIT_R1 = """
## Harness 元信息
| 字段 | 值 |
| **test_strategy** | `recommended` |

### 人工闸 `human_gate`
| human_gate_id | status | blocks_hats | 说明 |
| HG-TASK-DRAFT | approved | 30 | 探针示例 |

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


def test_build_10_spec_prompt():
    graph = load_graph("data/graph/sample_graph_v2.json")
    task = parse_task_markdown("data/tasks/sample_task.md")
    subgraph = query_subgraph(graph, task.entry_node, depth=2)
    compiled = build_hat_prompt("10-spec", graph, task, subgraph, [])
    assert "10-spec" in compiled.semi_static
    assert "R0–R5" in compiled.dynamic_suffix or "R0-R5" in compiled.dynamic_suffix
    assert "SPEC 草案" in compiled.dynamic_suffix


def test_build_10_task_prompt():
    graph = load_graph("data/graph/sample_graph_v2.json")
    task = parse_task_markdown("data/tasks/sample_task.md")
    subgraph = query_subgraph(graph, task.entry_node, depth=2)
    compiled = build_hat_prompt("10-task", graph, task, subgraph, [])
    assert "10-task" in compiled.semi_static
    assert "task.md 骨架" in compiled.dynamic_suffix
    assert "failure_paths" in compiled.dynamic_suffix


def test_build_20_review_prompt():
    graph = load_graph("data/graph/sample_graph_v2.json")
    task = parse_task_markdown("data/tasks/sample_task.md")
    task = task.model_copy(update={"review_target": "task"})
    subgraph = query_subgraph(graph, task.entry_node, depth=2)
    compiled = build_hat_prompt("20-review", graph, task, subgraph, [])
    assert "20-review" in compiled.semi_static
    assert "approved / blocked" in compiled.dynamic_suffix
    assert "HG-AUDIT-R1" in compiled.dynamic_suffix


def test_build_50_reinspect_prompt():
    graph = load_graph("data/graph/sample_graph_v2.json")
    task = parse_task_markdown("data/tasks/sample_task.md")
    task = task.model_copy(update={"reinspect_mode": "global"})
    subgraph = query_subgraph(graph, task.entry_node, depth=2)
    compiled = build_hat_prompt("50-reinspect", graph, task, subgraph, [])
    assert "50-reinspect global" in compiled.dynamic_suffix
    assert "failure_path_ref" in compiled.dynamic_suffix
    assert "CLOSE" in compiled.dynamic_suffix


def test_validate_human_gate_rules_ok():
    gates = [
        HumanGate(gate_id="HG-TASK-DRAFT", status="approved", blocks_hats=["22-R1", "30"]),
        HumanGate(gate_id="HG-AUDIT-R1", status="approved", blocks_hats=["30"]),
    ]
    assert validate_human_gate_rules(gates) == []


def test_validate_human_gate_missing():
    assert validate_human_gate_rules([]) == ["HUMAN-GATE-MISSING: task 须含 human_gate 表"]


def test_validate_audit_r1_missing():
    gates = [HumanGate(gate_id="HG-TASK-DRAFT", status="approved", blocks_hats=["30"])]
    errors = validate_human_gate_rules(gates)
    assert len(errors) == 1
    assert "HUMAN-GATE-AUDIT-R1-MISSING" in errors[0]


def test_validate_task_markdown(tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_text(TASK_HG_NO_AUDIT_R1, encoding="utf-8")
    errors = validate_task_markdown(bad)
    assert any("HUMAN-GATE-AUDIT-R1-MISSING" in e for e in errors)
