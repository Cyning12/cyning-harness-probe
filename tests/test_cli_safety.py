"""CLI 安全策略配置测试。"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from harness_probe.cli import main
from harness_sdk.executor import SubprocessExecutor
from harness_sdk.safety import SafetyConfigError, load_safety_config


REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def runner():
    """返回一个调用 CLI 的辅助函数。"""

    def _invoke(argv):
        return main(argv)

    return _invoke


@pytest.fixture
def temp_safety_config(tmp_path):
    """写入扩展白名单的 safety.yaml。"""
    config = tmp_path / "safety.yaml"
    config.write_text(
        "mode: whitelist\nallowed_commands:\n  - echo manual-verify\n  - pytest\n",
        encoding="utf-8",
    )
    return config


def _minimal_task_text() -> str:
    return (
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
        "`CLI`\n"
    )


def test_load_safety_config_extends_whitelist(tmp_path):
    config = tmp_path / "safety.yaml"
    config.write_text(
        "mode: whitelist\nallowed_commands:\n  - custom-test-cmd\n",
        encoding="utf-8",
    )
    cfg = load_safety_config(config)
    assert "custom-test-cmd" in cfg.allowed_commands
    assert "pytest" in cfg.allowed_commands


def test_load_safety_config_ignores_dangerous_prefix_override(tmp_path):
    config = tmp_path / "safety.yaml"
    config.write_text(
        "mode: whitelist\ndangerous_prefixes:\n  - rm\n  - myprefix\n",
        encoding="utf-8",
    )
    with pytest.warns(UserWarning, match="dangerous_prefix_override_ignored"):
        cfg = load_safety_config(config)
    assert "rm" in cfg.dangerous_prefixes
    assert "myprefix" in cfg.dangerous_prefixes


def test_load_safety_config_missing_returns_default(tmp_path):
    missing = tmp_path / "missing.yaml"
    with pytest.warns(UserWarning, match="safety_config_not_found"):
        cfg = load_safety_config(missing)
    assert cfg.mode.value == "whitelist"
    assert "pytest" in cfg.allowed_commands


def test_load_safety_config_invalid_yaml_raises(tmp_path):
    config = tmp_path / "bad.yaml"
    config.write_text("mode: [unclosed", encoding="utf-8")
    with pytest.raises(SafetyConfigError, match="invalid_safety_yaml"):
        load_safety_config(config)


async def _run_executor(cmd: str, safety_mode: str = "whitelist"):
    executor = SubprocessExecutor(safety_mode=safety_mode)
    return await executor.run(cmd)


def test_safety_config_blocked_reason_readable():
    result = asyncio.run(_run_executor("unknown-cmd"))
    assert result.blocked is True
    assert result.reason is not None
    assert "not_in_whitelist" in result.reason
    assert "config/safety.yaml" in result.reason


def test_cli_safety_config_real_executor(tmp_path, runner, temp_safety_config):
    """--safety-config 扩展白名单后命令放行。"""
    task = tmp_path / "task.md"
    task.write_text(_minimal_task_text(), encoding="utf-8")
    ret = runner(
        [
            "run",
            "--task",
            str(task),
            "--executor",
            "real",
            "--safety-config",
            str(temp_safety_config),
            "--graph",
            str(REPO_ROOT / "docs" / "_tech_graph" / "graph.json"),
            "--quiet",
        ]
    )
    assert ret == 0


def test_cli_safety_config_missing_warns_and_runs_default(tmp_path, runner):
    """--safety-config 不存在时回退默认配置。"""
    task = tmp_path / "task.md"
    task.write_text(_minimal_task_text(), encoding="utf-8")
    ret = runner(
        [
            "run",
            "--task",
            str(task),
            "--executor",
            "real",
            "--safety-config",
            str(tmp_path / "missing.yaml"),
            "--graph",
            str(REPO_ROOT / "docs" / "_tech_graph" / "graph.json"),
            "--quiet",
        ]
    )
    assert ret == 0


def test_cli_safety_config_invalid_yaml_exits(tmp_path, runner):
    """--safety-config YAML 解析失败时退出码 2。"""
    task = tmp_path / "task.md"
    task.write_text(_minimal_task_text(), encoding="utf-8")
    bad = tmp_path / "bad.yaml"
    bad.write_text("mode: [unclosed", encoding="utf-8")
    ret = runner(
        [
            "run",
            "--task",
            str(task),
            "--executor",
            "real",
            "--safety-config",
            str(bad),
            "--graph",
            str(REPO_ROOT / "docs" / "_tech_graph" / "graph.json"),
            "--quiet",
        ]
    )
    assert ret == 2


@pytest.mark.asyncio
async def test_subprocess_executor_with_custom_safety_config(tmp_path):
    """SubprocessExecutor 接受自定义 SafetyConfig。"""
    config = tmp_path / "safety.yaml"
    config.write_text(
        "allowed_commands:\n  - echo hello\n",
        encoding="utf-8",
    )
    cfg = load_safety_config(config)
    executor = SubprocessExecutor(safety_mode="whitelist", safety_config=cfg)
    result = await executor.run("echo hello")
    assert result.returncode == 0

    result = await executor.run("unknown-cmd")
    assert result.blocked is True
