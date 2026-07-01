"""Tests for harness_sdk/task_schema.py"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from harness_sdk.task_schema import (
    AcceptanceItem,
    FailurePath,
    HumanGate,
    HumanGateStatus,
    TaskInfo,
    TaskSchema,
    TestStrategy,
)


def test_human_gate_approved():
    gate = HumanGate(gate_id="HG-AUDIT-R1", status="approved", blocks_hats=[30])
    assert gate.status == HumanGateStatus.approved
    assert gate.blocks_hat(30)


def test_human_gate_completed_normalized():
    with pytest.warns(DeprecationWarning, match="completed.*deprecated"):
        gate = HumanGate(gate_id="HG-TASK-DRAFT", status="completed", blocks_hats="30")
    assert gate.status == HumanGateStatus.approved
    assert gate.blocks_hats == [30]


def test_human_gate_invalid_status():
    with pytest.raises(ValidationError):
        HumanGate(gate_id="HG-X", status="rejected", blocks_hats=[30])


def test_human_gate_blocks_hats_must_be_integers():
    with pytest.raises(ValidationError):
        HumanGate(gate_id="HG-X", status="approved", blocks_hats=["a"])


def test_failure_path_retry_normalization():
    fp = FailurePath(trigger="t", behavior="b", retry="是", visible_type="error")
    assert fp.retry is True
    fp2 = FailurePath(trigger="t", behavior="b", retry="否", visible_type="error")
    assert fp2.retry is False


def test_task_info_test_strategy_enum():
    info = TaskInfo(test_strategy="required")
    assert info.test_strategy == TestStrategy.required

    info2 = TaskInfo(test_strategy="n/a")
    assert info2.test_strategy == TestStrategy.not_applicable

    with pytest.raises(ValidationError):
        TaskInfo(test_strategy="optional")


def test_task_schema_graph_delta_missing():
    with pytest.raises(ValidationError, match="graph_delta file not found"):
        TaskSchema(
            metadata=TaskInfo(graph_delta="docs/_tech_graph/missing.graph.yaml")
        )


def test_task_schema_graph_delta_none_allowed():
    schema = TaskSchema(metadata=TaskInfo(graph_delta="none"))
    assert schema.metadata.graph_delta == "none"


def test_task_schema_graph_delta_existing(tmp_path: Path):
    existing = tmp_path / "delta.graph.yaml"
    existing.write_text("graph_id: test\n", encoding="utf-8")
    # 使用绝对路径绕过仓库相对路径检查
    schema = TaskSchema(
        metadata=TaskInfo(graph_delta=str(existing)),
    )
    assert schema.metadata.graph_delta == str(existing)


def test_task_schema_blocking_gates():
    schema = TaskSchema(
        metadata=TaskInfo(
            human_gates=[
                HumanGate(gate_id="G1", status="pending", blocks_hats=[30]),
                HumanGate(gate_id="G2", status="approved", blocks_hats=[30]),
                HumanGate(gate_id="G3", status="pending", blocks_hats=[40]),
            ]
        )
    )
    blocking = schema.blocking_gates("30")
    assert len(blocking) == 1
    assert blocking[0].gate_id == "G1"


def test_task_schema_is_gate_approved():
    schema = TaskSchema(
        metadata=TaskInfo(
            human_gates=[
                HumanGate(gate_id="G1", status="approved"),
                HumanGate(gate_id="G2", status="pending"),
            ]
        )
    )
    assert schema.is_gate_approved("G1")
    assert not schema.is_gate_approved("G2")


def test_acceptance_item():
    item = AcceptanceItem(text="do thing", checked=True)
    assert item.checked
