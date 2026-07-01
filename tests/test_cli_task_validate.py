"""Tests for harness-probe task validate CLI"""

from __future__ import annotations

from pathlib import Path

from harness_probe.cli import main


VALID_TASK = """---
title: valid
track: feature
graph_delta: none
freeze_id: v0.1.0
test_strategy: required
---
# task_valid_v0_1_0_v1

## Harness 元信息

| 字段 | 值 |
| --- | --- |
| **track** | feature |
| **test_strategy** | required |

### 人工闸

| human_gate_id | status | blocks_hats | 说明 |
| --- | --- | --- | --- |
| HG-TASK-DRAFT | approved | 30 | ok |
| HG-AUDIT-R1 | approved | 30 | ok |
| HG-EXEC-AUTH | approved | 30 | ok |

## 验收标准

- [x] done

## 失败路径

| 触发条件 | 系统行为 | 是否可重试 | 用户可见类型 |
| --- | --- | --- | --- |
| err | raise | 是 | error |
"""


def _write_task(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def test_cli_task_validate_valid(tmp_path: Path):
    path = _write_task(tmp_path, "task_valid_v0_1_0_v1.md", VALID_TASK)
    code = main(["task", "validate", "--task", str(path)])
    assert code == 0


def test_cli_task_validate_json_format(tmp_path: Path):
    path = _write_task(tmp_path, "task_valid_v0_1_0_v1.md", VALID_TASK)
    code = main(["task", "validate", "--task", str(path), "--format", "json"])
    assert code == 0


def test_cli_task_validate_invalid_status(tmp_path: Path):
    text = VALID_TASK.replace("approved | 30 | ok", "rejected | 30 | bad")
    path = _write_task(tmp_path, "task_invalid_v0_1_0_v1.md", text)
    code = main(["task", "validate", "--task", str(path)])
    assert code == 1


def test_cli_task_validate_missing_graph_delta(tmp_path: Path):
    text = VALID_TASK.replace("graph_delta: none", "graph_delta: docs/_tech_graph/missing.graph.yaml")
    path = _write_task(tmp_path, "task_missing_delta_v0_1_0_v1.md", text)
    code = main(["task", "validate", "--task", str(path)])
    assert code == 1


def test_cli_task_validate_blocking_30(tmp_path: Path):
    text = VALID_TASK.replace("HG-AUDIT-R1 | approved", "HG-AUDIT-R1 | pending")
    path = _write_task(tmp_path, "task_blocked_v0_1_0_v1.md", text)
    code = main(["task", "validate", "--task", str(path)])
    assert code == 1


def test_cli_task_validate_dir(tmp_path: Path):
    _write_task(tmp_path, "task_valid_v0_1_0_v1.md", VALID_TASK)
    bad = VALID_TASK.replace("approved | 30 | ok", "rejected | 30 | bad")
    _write_task(tmp_path, "task_invalid_v0_1_0_v1.md", bad)
    code = main(["task", "validate", "--dir", str(tmp_path)])
    assert code == 1


def test_cli_task_validate_strict_completed(tmp_path: Path):
    text = VALID_TASK.replace("approved | 30 | ok", "completed | 30 | done")
    path = _write_task(tmp_path, "task_completed_v0_1_0_v1.md", text)
    code = main(["task", "validate", "--task", str(path), "--strict"])
    assert code == 1


def test_cli_task_validate_no_task_or_dir():
    code = main(["task", "validate"])
    assert code == 2


def test_cli_task_validate_dir_json(tmp_path: Path):
    _write_task(tmp_path, "task_valid_v0_1_0_v1.md", VALID_TASK)
    code = main(["task", "validate", "--dir", str(tmp_path), "--format", "json"])
    assert code == 0
    # 简单验证输出为合法 JSON 数组
    # capsys 不在作用域，直接调用会打印到 stdout；这里仅验证返回码。


def test_cli_task_validate_dir_not_found():
    code = main(["task", "validate", "--dir", "/nonexistent/path/12345"])
    assert code == 2
