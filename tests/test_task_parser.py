"""Tests for harness_sdk/task_parser.py"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from harness_sdk.task_parser import (
    parse_acceptance_items,
    parse_failure_paths,
    parse_human_gates,
    parse_meta_table,
    parse_sections,
    parse_task_file,
    parse_task_text,
    split_frontmatter,
)
from harness_sdk.task_schema import HumanGateStatus, TestStrategy


SAMPLE_TASK = """---
title: sample
track: feature
freeze_id: v0.1.0
---

# task_sample

## Harness 元信息

| 字段 | 值 |
| --- | --- |
| **track** | `feature` |
| **test_strategy** | `required` |

### 人工闸 `human_gate`

| human_gate_id | status | blocks_hats | 说明 |
| --- | --- | --- | --- |
| HG-TASK-DRAFT | `approved` | 30 | ok |
| HG-AUDIT-R1 | `pending` | 30 | blocks |

## 背景与目标

bg text

## 范围

scope text

## 验收标准

- [x] done item
- [ ] todo item

## 失败路径

| 触发条件 | 系统行为 | 是否可重试 | 用户可见类型 |
| --- | --- | --- | --- |
| bad yaml | raise | 是 | error |
| missing field | list | 否 | field error |

## 实现备忘

notes
"""


def test_split_frontmatter():
    text = "---\ntitle: hi\n---\n# body"
    fm, body = split_frontmatter(text)
    assert fm == {"title": "hi"}
    assert body == "# body"


def test_split_frontmatter_missing():
    text = "# no frontmatter"
    fm, body = split_frontmatter(text)
    assert fm is None
    assert body == text


def test_parse_meta_table():
    meta = parse_meta_table(SAMPLE_TASK)
    assert meta["track"] == "feature"
    assert meta["test_strategy"] == "required"


def test_parse_human_gates():
    gates = parse_human_gates(SAMPLE_TASK)
    assert len(gates) == 2
    assert gates[0].gate_id == "HG-TASK-DRAFT"
    assert gates[0].status == HumanGateStatus.approved
    assert gates[1].blocks_hats == [30]


def test_parse_acceptance_items():
    items = parse_acceptance_items(SAMPLE_TASK)
    assert len(items) == 2
    assert items[0].checked
    assert not items[1].checked


def test_parse_failure_paths():
    paths = parse_failure_paths(SAMPLE_TASK)
    assert len(paths) == 2
    assert paths[0].trigger == "bad yaml"
    assert paths[0].retry is True
    assert paths[1].retry is False


def test_parse_sections():
    sections = parse_sections(SAMPLE_TASK)
    assert "背景与目标" in sections
    assert "范围" in sections
    assert "实现备忘" in sections


def test_parse_task_text_full():
    schema, warns = parse_task_text(SAMPLE_TASK)
    assert schema.metadata.track == "feature"
    assert schema.metadata.test_strategy == TestStrategy.required
    assert len(schema.metadata.human_gates) == 2
    assert len(schema.metadata.acceptance) == 2
    assert len(schema.metadata.failure_paths) == 2
    assert "背景与目标" in schema.content


def test_parse_task_text_completed_status_emits_warning():
    text = """---
freeze_id: v0.1.0
---
### 人工闸
| human_gate_id | status | blocks_hats |
| --- | --- | --- |
| HG-X | `completed` | 30 |
"""
    with pytest.warns(DeprecationWarning):
        schema, _ = parse_task_text(text)
    assert schema.metadata.human_gates[0].status == HumanGateStatus.approved


def test_parse_task_file_with_real_task(tmp_path: Path):
    task = tmp_path / "task_project_v0_1_0_x_v1.md"
    task.write_text(SAMPLE_TASK, encoding="utf-8")
    schema, _ = parse_task_file(task)
    assert schema.metadata.track == "feature"


def test_parse_task_file_missing_graph_delta(tmp_path: Path):
    text = """---
graph_delta: docs/_tech_graph/missing.graph.yaml
---
### 人工闸
| human_gate_id | status | blocks_hats |
| --- | --- | --- |
| HG-X | approved | 30 |
"""
    task = tmp_path / "task.md"
    task.write_text(text, encoding="utf-8")
    with pytest.raises(ValidationError):
        parse_task_file(task)
