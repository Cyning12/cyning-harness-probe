"""L1 编译：task failure_paths → AcceptanceContract；Wiki 检索"""

from __future__ import annotations

import json
import re
from pathlib import Path

from src.models import AcceptanceContract, HarnessTask, HumanGate, WikiEntry


FAILURE_TABLE_HEADER = re.compile(r"^\|\s*触发条件\s*\|", re.MULTILINE)
TABLE_ROW = re.compile(
    r"^\|\s*(?P<trigger>[^|]+)\|\s*(?P<expected>[^|]+)\|\s*(?P<retry>[^|]+)\|\s*(?P<visible>[^|]+)\|",
    re.MULTILINE,
)
GATE_ROW = re.compile(
    r"^\|\s*(?P<gate_id>HG-[A-Z0-9-]+)\s*\|\s*`?(?P<status>pending|approved)`?\s*\|\s*(?P<blocks>[^|]+)\|",
    re.MULTILINE,
)
ENTRY_NODE = re.compile(r"^## entry_node\s*\n\s*`(?P<node>[^`]+)`", re.MULTILINE)
FREEZE_ID = re.compile(r"\*\*freeze_id\*\*：`([^`]+)`")


def parse_task_markdown(path: str | Path, dynamic_query: str = "") -> HarnessTask:
    text = Path(path).read_text(encoding="utf-8")
    freeze = FREEZE_ID.search(text)
    entry = ENTRY_NODE.search(text)
    contracts = compile_contracts_from_task(text)
    gates = parse_human_gates(text)
    branch_match = re.search(r"\*\*git_branch\*\*：`([^`]+)`", text)
    return HarnessTask(
        task_path=str(path),
        freeze_id=freeze.group(1) if freeze else None,
        git_branch=branch_match.group(1) if branch_match else "task/probe",
        entry_node=entry.group("node") if entry else "RAG",
        contracts=contracts,
        human_gates=gates,
        dynamic_query=dynamic_query or "Probe dry-run：验证 Prompt 编译",
    )


def compile_contracts_from_task(text: str, max_rows: int = 15) -> list[AcceptanceContract]:
    section = _extract_section(text, "失败路径")
    if not section or not FAILURE_TABLE_HEADER.search(section):
        return []
    contracts: list[AcceptanceContract] = []
    for match in TABLE_ROW.finditer(section):
        trigger = match.group("trigger").strip()
        if trigger in ("触发条件", "----------", "---"):
            continue
        if len(contracts) >= max_rows:
            break
        idx = len(contracts) + 1
        expected = match.group("expected").strip()
        retry_raw = match.group("retry").strip()
        retry = "yes" if retry_raw.startswith("是") else "no" if retry_raw.startswith("否") else retry_raw
        verify = _suggest_verify(trigger, expected)
        contracts.append(
            AcceptanceContract(
                ref=f"F{idx}",
                trigger=trigger,
                expected=expected,
                retry=retry,
                verify=verify,
            )
        )
    return contracts


def _extract_section(text: str, heading_keyword: str) -> str:
    """截取 ## …heading_keyword… 至下一 ## 之间的正文"""
    pattern = re.compile(
        rf"^##[^\n]*{re.escape(heading_keyword)}[^\n]*\n(.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    return match.group(1) if match else ""


def _suggest_verify(trigger: str, expected: str) -> str:
    if "hits" in trigger and "0" in trigger:
        return "pytest tests/test_rag_fallback.py -k test_hits_zero  # 示例"
    if "RPC" in trigger or "超时" in trigger:
        return "pytest tests/test_rpc_retry.py  # 示例"
    if "verify" in trigger.lower() or "blocked" in expected.lower():
        return "python -m src.probe verify --entry RAG  # 探针自检"
    return "echo manual-verify  # 待 task 回填具体命令"


def parse_human_gates(text: str) -> list[HumanGate]:
    section = _extract_section(text, "人工闸")
    if not section:
        return []
    gates: list[HumanGate] = []
    for match in GATE_ROW.finditer(section):
        blocks = [b.strip() for b in match.group("blocks").split(",") if b.strip()]
        gates.append(
            HumanGate(
                gate_id=match.group("gate_id"),
                status=match.group("status"),  # type: ignore[arg-type]
                blocks_hats=blocks,
            )
        )
    return gates


def validate_human_gate_rules(gates: list[HumanGate]) -> list[str]:
    """校验 human_gate 表与 blocks_hats 规则（对齐 IMP-09 / PROMPT §4.5）。"""
    errors: list[str] = []
    if not gates:
        errors.append("HUMAN-GATE-MISSING: task 须含 human_gate 表")
        return errors

    blocks_values = set()
    for gate in gates:
        blocks_values.update(gate.blocks_hats)

    if "30" in blocks_values:
        audit_r1 = any(g.gate_id == "HG-AUDIT-R1" for g in gates)
        if not audit_r1:
            errors.append(
                "HUMAN-GATE-AUDIT-R1-MISSING: blocks_hats 含 30 时须含 HG-AUDIT-R1"
            )

    return errors


def validate_task_markdown(path: str | Path) -> list[str]:
    """对 task.md 执行 PRE_SPAWN_VERIFY 级静态校验。"""
    text = Path(path).read_text(encoding="utf-8")
    gates = parse_human_gates(text)
    return validate_human_gate_rules(gates)


def load_wiki_stub(path: str | Path) -> list[WikiEntry]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return [WikiEntry.model_validate(item) for item in raw]


def retrieve_wiki(
    entries: list[WikiEntry],
    query: str,
    entry_node: str,
    top_k: int = 3,
) -> list[WikiEntry]:
    """轻量检索：graph_nodes 命中 + 标题/摘要关键词"""
    scored: list[tuple[int, WikiEntry]] = []
    q = query.lower()
    for entry in entries:
        score = 0
        if entry_node in entry.graph_nodes:
            score += 3
        if any(token in entry.summary.lower() for token in q.split()):
            score += 1
        if score > 0:
            scored.append((score, entry))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [e for _, e in scored[:top_k]] or entries[:top_k]


def format_wiki_context(entries: list[WikiEntry]) -> str:
    if not entries:
        return "（无 L2 摘要命中）"
    lines = []
    for entry in entries:
        nodes = ", ".join(entry.graph_nodes) if entry.graph_nodes else "—"
        lines.append(f"- **{entry.title}**（nodes: {nodes}）\n  {entry.summary}")
    return "\n".join(lines)


def format_contract_table(contracts: list[AcceptanceContract]) -> str:
    header = "| ref | trigger | expected | retry | verify |\n|-----|---------|----------|-------|--------|\n"
    rows = [
        f"| {c.ref} | {c.trigger} | {c.expected} | {c.retry} | {c.verify} |"
        for c in contracts
    ]
    return header + "\n".join(rows)
