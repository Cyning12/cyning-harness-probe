"""Harness Probe · 文件 IO 与渲染"""

from __future__ import annotations

import json
import re
from pathlib import Path

from harness_sdk.compiler import (
    compile_contracts_from_task,
    parse_human_gates,
    validate_human_gate_rules,
)
from harness_sdk.models import CompiledPrompt, HarnessTask, TaskRunGraph, TechGraph, WikiEntry


ENTRY_NODE = re.compile(r"^## entry_node\s*\n\s*`(?P<node>[^`]+)`", re.MULTILINE)
FREEZE_ID = re.compile(r"\*\*freeze_id\*\*`([^`]+)`")


def load_graph(path: str | Path) -> TechGraph:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return TechGraph.model_validate(raw)


def parse_task_markdown(path: str | Path, dynamic_query: str = "") -> HarnessTask:
    text = Path(path).read_text(encoding="utf-8")
    freeze = FREEZE_ID.search(text)
    entry = ENTRY_NODE.search(text)
    contracts = compile_contracts_from_task(text)
    gates = parse_human_gates(text)
    branch_match = re.search(r"\*\*git_branch\*\*`([^`]+)`", text)
    return HarnessTask(
        task_path=str(path),
        freeze_id=freeze.group(1) if freeze else None,
        git_branch=branch_match.group(1) if branch_match else "task/probe",
        entry_node=entry.group("node") if entry else "RAG",
        contracts=contracts,
        human_gates=gates,
        dynamic_query=dynamic_query or "Probe dry-run：验证 Prompt 编译",
    )


def validate_task_markdown(path: str | Path) -> list[str]:
    """对 task.md 执行 PRE_SPAWN_VERIFY 级静态校验。"""
    text = Path(path).read_text(encoding="utf-8")
    gates = parse_human_gates(text)
    return validate_human_gate_rules(gates)


def load_wiki_stub(path: str | Path) -> list[WikiEntry]:
    p = Path(path)
    if not p.exists():
        return []
    raw = json.loads(p.read_text(encoding="utf-8"))
    return [WikiEntry.model_validate(item) for item in raw]


def persist_prompt(path: Path, compiled: CompiledPrompt) -> None:
    path.write_text(compiled.full_text, encoding="utf-8")


def persist_run_graph(path: Path, run_graph: TaskRunGraph) -> Path:
    path.write_text(
        run_graph.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return path
