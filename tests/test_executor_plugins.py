"""Executor plugin tests."""

from __future__ import annotations

import json

import pytest

from harness_sdk.executor import ExecutorPluginError, load_executor_plugin
from harness_sdk.executor_plugins import (
    DryRunExecutor,
    PreviewExecutor,
    SubprocessExecutor,
)
from harness_sdk.models import ExecutionResult
from harness_sdk.safety import PreviewRiskLevel


@pytest.mark.asyncio
async def test_load_dry_run_plugin():
    executor = load_executor_plugin("dry-run")
    assert isinstance(executor, DryRunExecutor)
    assert "dry-run" in executor.describe()


@pytest.mark.asyncio
async def test_load_preview_plugin():
    executor = load_executor_plugin("preview")
    assert isinstance(executor, PreviewExecutor)
    assert "preview" in executor.describe()


@pytest.mark.asyncio
async def test_load_subprocess_plugin():
    executor = load_executor_plugin("subprocess")
    assert isinstance(executor, SubprocessExecutor)
    assert "subprocess" in executor.describe()


@pytest.mark.asyncio
async def test_dry_run_executor_returns_dry_run_result():
    executor = DryRunExecutor()
    result = await executor.run("echo hello", session_id="s1")
    assert isinstance(result, ExecutionResult)
    assert result.returncode == 0
    assert result.dry_run is True
    assert result.reason == "dry-run"
    assert "[dry-run] echo hello" in result.stdout


@pytest.mark.asyncio
async def test_preview_executor_does_not_run_command():
    executor = PreviewExecutor()
    result = await executor.run("echo hello", session_id="s1")
    assert isinstance(result, ExecutionResult)
    assert result.returncode == 0
    assert result.reason == "preview"
    report = json.loads(result.stdout)
    assert report["cmd"] == "echo hello"
    assert report["risk_level"] == PreviewRiskLevel.low.value
    assert report["recommended_mode"] == "whitelist"


@pytest.mark.asyncio
async def test_subprocess_executor_runs_command():
    executor = SubprocessExecutor()
    result = await executor.run("echo real-test", session_id="s1")
    assert isinstance(result, ExecutionResult)
    assert result.returncode == 0
    assert result.stdout.strip() == "real-test"
    assert result.dry_run is False


@pytest.mark.asyncio
async def test_subprocess_executor_supports_and_describe():
    executor = SubprocessExecutor()
    assert executor.supports("any-cmd") is True
    assert "subprocess" in executor.describe()


def test_unknown_plugin_raises():
    with pytest.raises(ExecutorPluginError, match="unknown_executor_plugin"):
        load_executor_plugin("not-a-plugin")
