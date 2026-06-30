"""SDK compiler tests"""

from __future__ import annotations



from harness_sdk.compiler import (
    compile_contracts_from_task,
    format_contract_table,
    format_wiki_context,
    parse_human_gates,
    retrieve_wiki,
    validate_human_gate_rules,
)
from harness_sdk.models import HumanGate, WikiEntry


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


def test_parse_human_gates():
    gates = parse_human_gates(TASK_HG_NO_AUDIT_R1)
    assert len(gates) == 1
    assert gates[0].gate_id == "HG-TASK-DRAFT"
    assert gates[0].status == "approved"
    assert "30" in gates[0].blocks_hats


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


def test_retrieve_wiki_prefers_entry_node():
    entries = [
        WikiEntry(id="1", title="RAG", summary="about rag", graph_nodes=["RAG"]),
        WikiEntry(id="2", title="Other", summary="other", graph_nodes=["OTHER"]),
    ]
    hits = retrieve_wiki(entries, "query", "RAG", top_k=1)
    assert len(hits) == 1
    assert hits[0].id == "1"


def test_format_contract_table():
    contracts = compile_contracts_from_task(SAMPLE_TASK)
    table = format_contract_table(contracts)
    assert "| ref | trigger | expected | retry | verify |" in table
    assert "F1" in table


def test_format_wiki_context():
    entries = [WikiEntry(id="1", title="T", summary="S", graph_nodes=["RAG"])]
    ctx = format_wiki_context(entries)
    assert "T" in ctx
    assert "RAG" in ctx


def test_validate_task_markdown(tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_text(TASK_HG_NO_AUDIT_R1, encoding="utf-8")
    # validate_task_markdown is now in IO layer; test via parse + validate
    from harness_probe.io import parse_task_markdown
    task = parse_task_markdown(bad)
    errors = validate_human_gate_rules(task.human_gates)
    assert any("HUMAN-GATE-AUDIT-R1-MISSING" in e for e in errors)
