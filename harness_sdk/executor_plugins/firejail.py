"""Firejail sandbox executor plugin (Linux only)."""

from __future__ import annotations

import asyncio
import re
import shutil
import sys
import time
import uuid

from harness_sdk.audit.events import CapabilityAuditEvent
from harness_sdk.audit.logger import AuditLogger
from harness_sdk.capability import Capability
from harness_sdk.executor_plugins.sandbox import SandboxConfigError, SandboxExecutor
from harness_sdk.models import ExecutionResult


#: 支持 ``512m`` / ``1g`` / ``1024k`` / 纯数字字节。
_MEMORY_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([kmgt]?)b?\s*$", re.IGNORECASE)


def _parse_memory_to_bytes(value: str) -> int:
    """将 executor 配置中的内存字符串解析为字节数。"""
    match = _MEMORY_RE.match(value)
    if not match:
        raise SandboxConfigError(f"invalid sandbox memory value: {value!r}")
    amount = float(match.group(1))
    unit = match.group(2).lower()
    multipliers = {"": 1, "k": 1024, "m": 1024**2, "g": 1024**3, "t": 1024**4}
    return int(amount * multipliers[unit])


class FirejailExecutor(SandboxExecutor):
    """使用 ``firejail`` 在 Linux 主机上做进程级沙箱。

    macOS 不提供 firejail；构造函数会给出明确错误提示，建议改用 ``DockerExecutor``。
    根据 ``capabilities`` 生成 ``--net=none``、``--whitelist``、``--blacklist`` 参数。
    """

    def __init__(
        self,
        image: str | None = None,
        timeout: float | None = None,
        network: bool | None = None,
        memory: str | None = None,
        cpu: float | None = None,
        capabilities=None,
    ):
        if sys.platform != "linux":
            raise SandboxConfigError(
                "Firejail is Linux only. On macOS use Docker executor instead."
            )
        super().__init__(
            image=image,
            timeout=timeout,
            network=network,
            memory=memory,
            cpu=cpu,
            capabilities=capabilities,
        )

    async def run(
        self,
        cmd: str,
        cwd: str | None = None,
        session_id: str | None = None,
    ) -> ExecutionResult:
        firejail = shutil.which("firejail")
        if not firejail:
            raise SandboxConfigError(
                "firejail not installed. Install firejail on Linux to use this executor."
            )

        args = [firejail, "--noprofile"]
        if Capability.network not in self.config.capabilities:
            args.append("--net=none")
        args.extend(["--rlimit-as", str(_parse_memory_to_bytes(self.config.memory))])
        args.extend(["--rlimit-cpu", str(int(self.config.timeout))])

        # 根据 read/write 能力生成 whitelist/blacklist
        if cwd:
            if Capability.read in self.config.capabilities or Capability.write in self.config.capabilities:
                args.extend(["--whitelist", cwd])
            else:
                args.extend(["--blacklist", cwd])

        # 通过 sh -c 执行，使管道、重定向等 shell 语义与宿主机一致。
        args.extend(["sh", "-c", cmd])

        self._audit(
            session_id=session_id,
            cmd=cmd,
            firejail_args=args,
            granted=self.config.capabilities.to_list(),
        )

        started = time.perf_counter()
        proc: asyncio.subprocess.Process | None = None
        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(), timeout=self.config.timeout
            )
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return ExecutionResult(
                returncode=proc.returncode or 0,
                stdout=stdout_b.decode(errors="replace"),
                stderr=stderr_b.decode(errors="replace"),
                elapsed_ms=elapsed_ms,
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
                stderr=f"timeout after {self.config.timeout}s",
                elapsed_ms=elapsed_ms,
                timed_out=True,
            )
        except SandboxConfigError:
            raise
        except Exception as exc:
            raise SandboxConfigError(f"firejail run failed: {exc}") from exc

    def _audit(
        self,
        *,
        session_id: str | None,
        cmd: str,
        firejail_args: list[str],
        granted: list[str],
    ) -> None:
        """执行前写入 CapabilityAuditEvent。"""
        try:
            logger = AuditLogger()
            logger.log_event(
                CapabilityAuditEvent(
                    run_id=session_id or uuid.uuid4().hex,
                    task="firejail-sandbox-execution",
                    hat="30",
                    executor_plugin="firejail",
                    cmd=cmd,
                    granted_capabilities=granted,
                    sandbox_args=firejail_args,
                )
            )
        except Exception:
            pass
