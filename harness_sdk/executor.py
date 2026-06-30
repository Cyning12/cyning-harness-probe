"""Harness SDK · VerifyExecutor 实现（v0.7）"""

from __future__ import annotations

import asyncio
import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from harness_sdk.models import ExecutionResult
from harness_sdk.safety import CommandSafetyChecker, SafetyConfig, SafetyMode


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


class SubprocessExecutor:
    """真实子进程执行器：通过 shell 运行 verify 命令。"""

    def __init__(
        self,
        timeout: float = 60.0,
        max_stdout: int = 4096,
        *,
        safety_mode: str | SafetyMode = SafetyMode.whitelist,
        dry_run: bool = False,
        execution_log_dir: str | Path | None = None,
    ):
        self.timeout = timeout
        self.max_stdout = max_stdout
        if isinstance(safety_mode, str):
            safety_mode = SafetyMode(safety_mode)
        self.safety_mode = safety_mode
        self.dry_run = dry_run
        self.execution_log_dir = Path(execution_log_dir) if execution_log_dir else None
        self._checker = CommandSafetyChecker(SafetyConfig(mode=safety_mode))

    async def run(
        self,
        cmd: str,
        cwd: str | None = None,
        session_id: str | None = None,
    ) -> ExecutionResult:
        if self.dry_run:
            result = ExecutionResult(
                returncode=0,
                stdout=f"[dry-run] {cmd}",
                stderr="",
                elapsed_ms=0,
                dry_run=True,
                reason="dry-run",
            )
            self._log_event(session_id, "dry_run", cmd, cwd, result)
            return result

        check = self._checker.check(cmd)
        if not check.allowed:
            result = ExecutionResult(
                returncode=-2,
                stdout="",
                stderr=check.reason or "blocked",
                elapsed_ms=0,
                blocked=True,
                reason=check.reason,
            )
            self._log_event(session_id, "blocked", cmd, cwd, result)
            return result

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
            result = ExecutionResult(
                returncode=proc.returncode or 0,
                stdout=stdout,
                stderr=stderr,
                elapsed_ms=elapsed_ms,
                truncated=truncated,
            )
            self._log_event(session_id, "executed", cmd, cwd, result)
            return result
        except asyncio.TimeoutError:
            if proc is not None and proc.returncode is None:
                try:
                    proc.kill()
                    await proc.wait()
                except ProcessLookupError:
                    pass
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            result = ExecutionResult(
                returncode=-1,
                stdout="",
                stderr=f"timeout after {self.timeout}s",
                elapsed_ms=elapsed_ms,
                timed_out=True,
            )
            self._log_event(session_id, "timeout", cmd, cwd, result)
            return result

    def _log_event(
        self,
        session_id: str | None,
        event: str,
        cmd: str,
        cwd: str | None,
        result: ExecutionResult,
    ) -> None:
        if self.execution_log_dir is None:
            return
        self.execution_log_dir.mkdir(parents=True, exist_ok=True)
        log_path = self.execution_log_dir / f"execution_log_{session_id or 'unknown'}.jsonl"
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "event": event,
            "cmd": cmd,
            "cwd": cwd,
            "mode": self.safety_mode.value,
            "dry_run": result.dry_run,
            "blocked": result.blocked,
            "returncode": result.returncode,
            "reason": result.reason,
            "elapsed_ms": result.elapsed_ms,
        }
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
