"""MCP tool 安全参数测试。"""

from __future__ import annotations

import json
import os

import pytest

from harness_mcp.tools import probe_run


@pytest.fixture
def temp_task(tmp_path):
    task = tmp_path / "task.md"
    task.write_text(
        "# Task：Test\n\n"
        "> **状态**：approved_for_execution\n"
        "> **freeze_id**：`V0-TEST`\n"
        "> **graph_delta**：`docs/_tech_graph/90_executor.graph.yaml`\n"
        "> **test_strategy**：`required`\n\n"
        "### 人工闸 `human_gate`\n\n"
        "| human_gate_id | status | blocks_hats | 说明 |\n"
        "|---------------|--------|-------------|------|\n"
        "| HG-TASK-DRAFT | approved | 30 | 示例 |\n"
        "| HG-AUDIT-R1 | approved | 30 | 示例 |\n\n"
        "---\n\n"
        "## 背景与目标\n\n测试安全执行器。\n\n---\n\n"
        "## 失败路径\n\n"
        "| 触发条件 | 系统行为 | 可重试 | 用户可见 |\n"
        "|----------|----------|--------|----------|\n"
        "| 自定义命令执行失败 | returncode != 0 | 否 | 错误 |\n\n"
        "---\n\n"
        "## 验收标准\n\n"
        "- [ ] 自定义命令可执行\n\n"
        "---\n\n"
        "## entry_node\n\n"
        "`ROOT`\n",
        encoding="utf-8",
    )
    return task


@pytest.fixture
def temp_safety_config(tmp_path):
    config = tmp_path / "safety.yaml"
    config.write_text(
        "allowed_commands:\n  - custom-test-cmd\n  - echo\n",
        encoding="utf-8",
    )
    return config


@pytest.fixture
def temp_graph(tmp_path):
    """创建一个最小 graph.json。"""
    graph = tmp_path / "graph.json"
    graph.write_text(
        json.dumps(
            {
                "nodes": [
                    {"id": "ROOT", "label": "root", "kind": "entry"},
                    {"id": "30", "label": "30", "kind": "hat"},
                    {"id": "40", "label": "40", "kind": "hat"},
                ],
                "edges": [
                    {"from": "ROOT", "to": "30", "label": "->"},
                    {"from": "30", "to": "40", "label": "->"},
                ],
                "freeze_id": "v0.7.1",
            }
        ),
        encoding="utf-8",
    )
    return graph


@pytest.mark.asyncio
async def test_mcp_probe_run_with_safety_config(
    tmp_path, temp_task, temp_safety_config, temp_graph
):
    """probe_run 使用 safety_config 扩展白名单。"""
    result = await probe_run(
        task_path=str(temp_task),
        entry_node="ROOT",
        from_hat="30",
        to_hat="40",
        graph_path=str(temp_graph),
        wiki_path=str(tmp_path / "wiki.json"),
        executor="real",
        safety_config=str(temp_safety_config),
    )
    data = json.loads(result)
    assert data["ok"] is True
    assert data["status"] == "done"


@pytest.mark.asyncio
async def test_mcp_probe_run_dry_run_no_execution(
    tmp_path, temp_task, temp_graph
):
    """dry_run=True 不实际执行。"""
    result = await probe_run(
        task_path=str(temp_task),
        entry_node="ROOT",
        from_hat="30",
        to_hat="40",
        graph_path=str(temp_graph),
        wiki_path=str(tmp_path / "wiki.json"),
        executor="real",
        dry_run=True,
    )
    data = json.loads(result)
    assert data["ok"] is True
    assert data["status"] == "done"


@pytest.mark.asyncio
async def test_mcp_probe_run_unsafe_requires_env(
    tmp_path, temp_task, temp_graph
):
    """unsafe 模式需 HARNESS_UNSAFE=1。"""
    os.environ.pop("HARNESS_UNSAFE", None)
    result = await probe_run(
        task_path=str(temp_task),
        entry_node="ROOT",
        from_hat="30",
        to_hat="40",
        graph_path=str(temp_graph),
        wiki_path=str(tmp_path / "wiki.json"),
        executor="real",
        safety_mode="unsafe",
    )
    data = json.loads(result)
    assert data["ok"] is True
    # unsafe 未确认时，所有 verify 会被 blocked
    assert data["status"] == "blocked"
