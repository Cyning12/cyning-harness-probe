"""Docker sandbox executor plugin."""

from __future__ import annotations

import asyncio
import re
import shutil
import time
import uuid
from pathlib import Path

from harness_sdk.executor_plugins.sandbox import SandboxConfigError, SandboxExecutor
from harness_sdk.models import ExecutionResult


class DockerExecutor(SandboxExecutor):
    """使用 ``docker run`` 在临时容器内执行命令。

    不依赖 ``docker`` Python SDK，仅要求宿主机已安装 Docker CLI 且守护进程可达。
    """

    async def run(
        self,
        cmd: str,
        cwd: str | None = None,
        session_id: str | None = None,
    ) -> ExecutionResult:
        docker_bin = shutil.which("docker")
        if not docker_bin:
            raise SandboxConfigError(
                "Docker not installed. Install Docker and ensure 'docker' is in PATH."
            )

        container_name = self._make_container_name(session_id)
        args = [docker_bin, "run", "--rm", "--name", container_name]
        if not self.config.network:
            args.extend(["--network", "none"])
        args.extend(["--memory", self.config.memory])
        args.extend(["--cpus", str(self.config.cpu)])

        workdir: str | None = None
        if cwd:
            workdir = "/work"
            args.extend(["-v", f"{Path(cwd).resolve()}:{workdir}", "-w", workdir])

        args.extend([self.config.image, "sh", "-c", cmd])

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
