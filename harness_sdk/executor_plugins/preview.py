"""Preview executor plugin."""

from __future__ import annotations

import json
from dataclasses import asdict

from harness_sdk.models import ExecutionResult
from harness_sdk.safety import CommandSafetyChecker, PreviewReport, SafetyConfig, SafetyMode


class PreviewExecutor:
    """不执行命令，仅返回命令沙箱预览报告。"""

    def __init__(
        self,
        *,
        safety_mode: str | SafetyMode = SafetyMode.whitelist,
        safety_config: SafetyConfig | None = None,
    ):
        if isinstance(safety_mode, str):
            safety_mode = SafetyMode(safety_mode)
        self.safety_mode = safety_mode
        if safety_config is None:
            safety_config = SafetyConfig(mode=safety_mode)
        else:
            safety_config.mode = safety_mode
        self._checker = CommandSafetyChecker(safety_config)

    def preview(self, cmd: str) -> PreviewReport:
        """生成命令沙箱预览报告（不执行命令）。"""
        return self._checker.preview(cmd)

    def supports(self, cmd: str) -> bool:
        return True

    def describe(self) -> str:
        return "preview executor (safety report, no subprocess)"

    async def run(
        self,
        cmd: str,
        cwd: str | None = None,
        session_id: str | None = None,
    ) -> ExecutionResult:
        report = self.preview(cmd)
        return ExecutionResult(
            returncode=0,
            stdout=json.dumps(asdict(report), ensure_ascii=False),
            stderr="",
            elapsed_ms=0,
            reason="preview",
        )
