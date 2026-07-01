"""Harness Task Schema · Pydantic 模型化任务单契约。

本模块不依赖文件 IO，仅负责：
- 定义任务单 Schema（TaskSchema / TaskInfo / HumanGate / AcceptanceItem / FailurePath）
- 提供字段级校验（status、blocks_hats、test_strategy、graph_delta 路径）
- 兼容旧字段（如 ``completed`` 自动映射为 ``approved``，但会发出 DeprecationWarning）
"""

from __future__ import annotations

import warnings
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


def _repo_root() -> Path:
    """harness_sdk 所在仓库根目录（基于本文件位置向上两级）。"""
    return Path(__file__).resolve().parent.parent


class HumanGateStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    completed = "completed"


class TestStrategy(str, Enum):
    required = "required"
    recommended = "recommended"
    not_applicable = "not_applicable"

    __test__ = False


class HumanGate(BaseModel):
    """人工闸表中的一行。"""

    gate_id: str
    status: HumanGateStatus
    blocks_hats: list[int] = Field(default_factory=list)
    description: str = ""

    @field_validator("status", mode="before")
    @classmethod
    def _normalize_status(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = value.strip().strip("`")
            if value == "completed":
                warnings.warn(
                    "human_gate status 'completed' is deprecated; use 'approved'",
                    DeprecationWarning,
                    stacklevel=2,
                )
                return HumanGateStatus.approved
        return value

    @field_validator("blocks_hats", mode="before")
    @classmethod
    def _normalize_blocks(cls, value: Any) -> Any:
        if isinstance(value, str):
            parts = [part.strip().strip("`") for part in value.split(",")]
            out: list[int] = []
            for part in parts:
                if not part:
                    continue
                try:
                    out.append(int(part))
                except ValueError as exc:
                    raise ValueError(
                        f"blocks_hats must be a list of integers; got {value!r}"
                    ) from exc
            return out
        return value

    def blocks_hat(self, hat: int | str) -> bool:
        """判断本闸是否阻塞指定 hat。"""
        return int(hat) in self.blocks_hats


class AcceptanceItem(BaseModel):
    """验收标准中的 ``- [ ]`` / ``- [x]`` 项。"""

    text: str
    checked: bool


class FailurePath(BaseModel):
    """失败路径表中的一行。"""

    trigger: str
    behavior: str
    retry: bool | str = False
    visible_type: str = ""

    @field_validator("retry", mode="before")
    @classmethod
    def _normalize_retry(cls, value: Any) -> Any:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("是"):
                return True
            if stripped.startswith("否"):
                return False
        return value


class TaskInfo(BaseModel):
    """任务单元信息 + 结构化内容。"""

    title: str = ""
    track: str = ""
    lightweight_task: str = ""
    module_id: str = ""
    graph_delta: str | None = None
    freeze_id: str | None = None
    test_strategy: TestStrategy | None = None
    human_gates: list[HumanGate] = Field(default_factory=list)
    acceptance: list[AcceptanceItem] = Field(default_factory=list)
    failure_paths: list[FailurePath] = Field(default_factory=list)
    background: str = ""
    scope: str = ""
    implementation_notes: str = ""

    @field_validator("test_strategy", mode="before")
    @classmethod
    def _normalize_test_strategy(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = value.strip().strip("`")
            if value == "n/a":
                return TestStrategy.not_applicable
        return value


class TaskSchema(BaseModel):
    """任务单顶层 Schema。"""

    metadata: TaskInfo = Field(default_factory=TaskInfo)
    content: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_graph_delta(self) -> TaskSchema:
        delta = self.metadata.graph_delta
        if not delta or delta.strip().lower() == "none":
            return self
        root = _repo_root()
        target = root / delta
        if not target.exists():
            raise ValueError(f"graph_delta file not found: {delta}")
        return self

    def is_gate_approved(self, gate_id: str) -> bool:
        for gate in self.metadata.human_gates:
            if gate.gate_id == gate_id:
                return gate.status == HumanGateStatus.approved
        return False

    def blocking_gates(self, hat: int | str) -> list[HumanGate]:
        """返回会阻塞指定 hat 执行的人闸列表。"""
        return [
            gate
            for gate in self.metadata.human_gates
            if gate.blocks_hat(hat) and gate.status != HumanGateStatus.approved
        ]

    def gate_by_id(self, gate_id: str) -> HumanGate | None:
        for gate in self.metadata.human_gates:
            if gate.gate_id == gate_id:
                return gate
        return None
