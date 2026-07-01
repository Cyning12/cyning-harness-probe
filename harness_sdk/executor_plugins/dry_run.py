"""Dry-run executor plugin."""

from __future__ import annotations

from harness_sdk.models import ExecutionResult


class DryRunExecutor:
    """不执行任何命令，返回标记为 dry-run 的 ExecutionResult。"""

    def supports(self, cmd: str) -> bool:
        return True

    def describe(self) -> str:
        return "dry-run executor (no subprocess)"

    async def run(
        self,
        cmd: str,
        cwd: str | None = None,
        session_id: str | None = None,
    ) -> ExecutionResult:
        return ExecutionResult(
            returncode=0,
            stdout=f"[dry-run] {cmd}",
            stderr="",
            elapsed_ms=0,
            dry_run=True,
            reason="dry-run",
        )
