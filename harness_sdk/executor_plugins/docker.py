"""Docker executor plugin."""

from __future__ import annotations

import asyncio
import re
import shutil
import time
import uuid
import warnings
from pathlib import Path

from harness_sdk.audit.events import CapabilityAuditEvent
from harness_sdk.audit.logger import AuditLogger
from harness_sdk.capability import Capability
from harness_sdk.executor_plugins.sandbox import SandboxConfigError, SandboxExecutor
from harness_sdk.models import ExecutionResult

class DockerExecutor(SandboxExecutor):
    """使用 ``docker run`` 在临时容器内执行命令。

    不依赖 ``docker`` Python SDK，仅要求宿主机已安装 Docker CLI 且守护进程可达。
    根据 ``capabilities`` 决定容器网络与挂载策略：
    - ``network`` 能力缺失时强制 ``--network none``
    - ``read`` 能力缺失时不挂载工作目录
    - ``write`` 能力缺失时以只读方式挂载工作目录
    """

    async def run(
        self,
        cmd: str,
        cwd: str | None = None,
        session_id: str | None = None,
    ) -> ExecutionResult:
        docker_bin = shutil.which("docker")
        if not docker_bin:
            # Docker 未安装且请求 network 能力时降级为 network=none 并继续尝试
            if Capability.network in self.config.capabilities:
                warnings.warn(
                    "Docker not installed; network capability will be unavailable",
                    stacklevel=2,
                )
            raise SandboxConfigError(
                "Docker not installed. Install Docker and ensure 'docker' is in PATH."
            )

        container_name = self._make_container_name(session_id)
        args = [docker_bin, "run", "--rm", "--name", container_name]

        # 网络策略：以 capability 为准
        if Capability.network not in self.config.capabilities:
            args.extend(["--network", "none"])
        elif self.config.network:
            args.extend(["--network", "host"])

        args.extend(["--memory", self.config.memory])
        args.extend(["--cpus", str(self.config.cpu)])

        workdir: str | None = None
        if cwd:
            workdir = "/work"
            host_path = Path(cwd).resolve()
            if Capability.read not in self.config.capabilities:
                # 无 read 能力时不挂载工作目录
                workdir = None
            elif Capability.write not in self.config.capabilities:
                args.extend(["-v", f"{host_path}:{workdir}:ro", "-w", workdir])
            else:
                args.extend(["-v", f"{host_path}:{workdir}", "-w", workdir])

        args.extend([self.config.image, "sh", "-c", cmd])

        self._audit(
            session_id=session_id,
            cmd=cmd,
            docker_args=args,
            granted=self.config.capabilities.to_list(),
        )

        started = time.perf_counter()
        proc: asyncio.subprocess.Process | None = None
        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
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
            return await self._handle_timeout(proc, container_name, started)
        except Exception as exc:
            await self._cleanup_container(container_name)
            raise SandboxConfigError(f"docker run failed: {exc}") from exc

    def _make_container_name(self, session_id: str | None) -> str:
        """生成符合 Docker 命名规则的容器名。"""
        base = f"harness-probe-{session_id or 'session'}-{uuid.uuid4().hex[:8]}"
        return re.sub(r"[^a-zA-Z0-9_.-]", "-", base)

    async def _handle_timeout(
        self,
        proc: asyncio.subprocess.Process | None,
        container_name: str,
        started: float,
    ) -> ExecutionResult:
        """超时后回收容器并返回 timed_out 结果。"""
        if proc is not None and proc.returncode is None:
            try:
                proc.kill()
                await proc.wait()
            except ProcessLookupError:
                pass
        await self._cleanup_container(container_name)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return ExecutionResult(
            returncode=-1,
            stdout="",
            stderr=f"timeout after {self.config.timeout}s",
            elapsed_ms=elapsed_ms,
            timed_out=True,
        )

    async def _cleanup_container(self, container_name: str) -> None:
        """尽力清理可能残留的容器，忽略任何错误。"""
        docker_bin = shutil.which("docker")
        if not docker_bin:
            return
        try:
            proc = await asyncio.create_subprocess_exec(
                docker_bin,
                "rm",
                "-f",
                container_name,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=10.0)
        except Exception:
            pass

    def _audit(
        self,
        *,
        session_id: str | None,
        cmd: str,
        docker_args: list[str],
        granted: list[str],
    ) -> None:
        """执行前写入 CapabilityAuditEvent。"""
        try:
            logger = AuditLogger()
            logger.log_event(
                CapabilityAuditEvent(
                    run_id=session_id or uuid.uuid4().hex,
                    task="docker-sandbox-execution",
                    hat="30",
                    executor_plugin="docker",
                    cmd=cmd,
                    granted_capabilities=granted,
                    sandbox_args=docker_args,
                )
            )
        except Exception:
            # 审计失败不应阻塞执行
            pass
