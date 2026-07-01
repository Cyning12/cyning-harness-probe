"""Harness SDK · VerifyExecutor plugin protocol."""

from __future__ import annotations

from typing import Protocol

from harness_sdk.models import ExecutionResult


class ExecutorPluginError(Exception):
    """插件加载、解析或执行器切换错误。"""


class VerifyExecutor(Protocol):
    """执行 contract.verify 命令的抽象协议。"""

    async def run(
        self,
        cmd: str,
        cwd: str | None = None,
        session_id: str | None = None,
    ) -> ExecutionResult:
        """执行命令并返回 ExecutionResult。"""
        ...

    def supports(self, cmd: str) -> bool:
        """返回当前执行器是否能处理该命令。"""
        ...

    def describe(self) -> str:
        """返回人类可读描述。"""
        ...
