"""Harness SDK · 数据模型（L0 / L1 / L1.5 / L2）"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


@dataclass
class ExecutionResult:
    """一次 verify 命令的执行结果。"""

    returncode: int
    stdout: str
    stderr: str
    elapsed_ms: int
    truncated: bool = False
    timed_out: bool = False
    blocked: bool = False
    dry_run: bool = False
    reason: str | None = None


class GraphAnchor(BaseModel):
    path: str
    symbol: str = ""
    line: int | None = None


class GraphNode(BaseModel):
    id: str
    label: str
    graph_id: str = "main"
    kind: str | None = None
    module_id: str | None = None


class GraphEdge(BaseModel):
    from_id: str = Field(alias="from")
    to_id: str = Field(alias="to")
    mark: str = "->"
    type: str = "depends_on"
    sync: bool = True
    graph_id: str = "main"
    label: str = ""
    anchors: list[GraphAnchor] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class TechGraph(BaseModel):
    schema_version: str = "graph_v2"
    freeze_id: str = "UNKNOWN"
    generated_at: str | None = None
    nodes: list[GraphNode]
    edges: list[GraphEdge]

    def node_map(self) -> dict[str, GraphNode]:
        return {n.id: n for n in self.nodes}


class AcceptanceContract(BaseModel):
    ref: str
    trigger: str
    expected: str
    retry: str
    verify: str


class HumanGate(BaseModel):
    gate_id: str
    status: Literal["pending", "approved"]
    blocks_hats: list[str] = Field(default_factory=list)


class HarnessTask(BaseModel):
    task_path: str
    freeze_id: str | None = None
    git_branch: str = "task/probe"
    entry_node: str = "RAG"
    planned_hats: list[str] = Field(default_factory=lambda: ["30", "40"])
    contracts: list[AcceptanceContract] = Field(default_factory=list)
    human_gates: list[HumanGate] = Field(default_factory=list)
    dynamic_query: str = ""
    spec_path: str | None = None
    spec_text: str = ""
    review_target: str | None = None
    run_output_path: str | None = None
    reinspect_mode: str = "independent"

    def is_gate_approved(self, gate_id: str) -> bool:
        for gate in self.human_gates:
            if gate.gate_id == gate_id:
                return gate.status == "approved"
        return False

    def blocks_hat(self, hat: str) -> HumanGate | None:
        for gate in self.human_gates:
            if gate.status != "approved" and hat in gate.blocks_hats:
                return gate
        return None


class WikiEntry(BaseModel):
    id: str
    title: str
    summary: str
    graph_nodes: list[str] = Field(default_factory=list)
    freeze_id: str | None = None


class SubgraphResult(BaseModel):
    entry_node: str
    depth: int
    node_ids: list[str]
    edges: list[GraphEdge]
    mermaid: str


class RunNodeStatus(str, Enum):
    pending = "pending"
    running = "running"
    done = "done"
    blocked = "blocked"
    skipped = "skipped"


class TaskRunNode(BaseModel):
    """L1.5 运行时实例图 · 单步节点"""

    id: str
    hat: str
    status: RunNodeStatus = RunNodeStatus.pending
    contract_refs: list[str] = Field(default_factory=list)
    evidence: str | None = None
    error: str | None = None


class TaskRunGraph(BaseModel):
    """L1.5 · 会话级任务执行图谱（用户/探针资产）"""

    session_id: str
    user_id: str = "probe-local"
    task_path: str
    l0_freeze_id: str
    entry_node: str
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    nodes: list[TaskRunNode] = Field(default_factory=list)
    status: Literal["running", "done", "blocked", "aborted"] = "running"

    def append_hat(self, hat: str, contract_refs: list[str]) -> TaskRunNode:
        node = TaskRunNode(id=f"hat-{hat}", hat=hat, contract_refs=contract_refs)
        self.nodes.append(node)
        return node


class CompiledPrompt(BaseModel):
    static_prefix: str
    semi_static: str
    dynamic_suffix: str
    static_char_count: int
    dynamic_char_count: int

    @property
    def full_text(self) -> str:
        return self.static_prefix + self.semi_static + self.dynamic_suffix
