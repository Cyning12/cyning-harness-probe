"""Harness SDK · VerifyExecutor 实现（v0.6-a1）"""

from __future__ import annotations

import asyncio
import shutil
import time
from typing import Protocol

from harness_sdk.models import ExecutionResult


class VerifyExecutor(Protocol):
    """执行 contract.verify 命令的抽象协议。"""

    async def run(self, cmd: str, cwd: str | None = None) -> ExecutionResult:
        """执行命令并返回 ExecutionResult。"""
        ...


class SubprocessExecutor:
    """真实子进程执行器：通过 shell 运行 verify 命令。"""

    def __init__(self, timeout: float = 60.0, max_stdout: int = 4096):
        self.timeout = timeout
        self.max_stdout = max_stdout

    async def run(self, cmd: str, cwd: str | None = None) -> ExecutionResult:
        shell = shutil.which("/bin/sh") or shutil.which("sh") or "/bin/sh"
        started = time.perf_counter()
        proc: asyncio.subprocess.Process | None = None
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                executable=shell,
            )
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout
            )
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            stdout = stdout_b.decode(errors="replace")
            stderr = stderr_b.decode(errors="replace")
            truncated = False
            if len(stdout) > self.max_stdout:
                stdout = stdout[: self.max_stdout] + "\n[truncated]"
                truncated = True
            return ExecutionResult(
                returncode=proc.returncode or 0,
                stdout=stdout,
                stderr=stderr,
                elapsed_ms=elapsed_ms,
                truncated=truncated,
            )
        except asyncio.TimeoutError:
            if proc is not None and proc.returncode is None:
                try:
                    proc.kill()
                    await proc.wait()
                except ProcessLookupError:
                    pass
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return ExecutionResult(
                returncode=-1,
                stdout="",
                stderr=f"timeout after {self.timeout}s",
                elapsed_ms=elapsed_ms,
                timed_out=True,
            )
