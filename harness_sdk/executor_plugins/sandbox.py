"""Sandbox executor base class and configuration helpers."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from harness_sdk.capability import Capability, CapabilitySet
from harness_sdk.executor_plugins.base import ExecutorPluginError
from harness_sdk.models import ExecutionResult


class SandboxConfigError(ExecutorPluginError):
    """沙箱参数非法或运行环境不满足时抛出。"""


@dataclass
class SandboxConfig:
    """沙箱通用参数。"""

    image: str = "python:3.11-slim"
    timeout: float = 60.0
    network: bool = False
    memory: str = "512m"
    cpu: float = 1.0
    capabilities: CapabilitySet = field(default_factory=CapabilitySet.default)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> SandboxConfig:
        """从 executor.yaml 的 sandbox 段构造配置。"""
        if not data:
            return cls()
        capabilities = data.get("capabilities")
        if capabilities is None:
            capabilities = CapabilitySet.default()
        else:
            capabilities = CapabilitySet(capabilities)
        return cls(
            image=str(data.get("image", cls.image)),
            timeout=float(data.get("timeout", cls.timeout)),
            network=bool(data.get("network", cls.network)),
            memory=str(data.get("memory", cls.memory)),
            cpu=float(data.get("cpu", cls.cpu)),
            capabilities=capabilities,
        )


def _load_executor_yaml() -> dict[str, Any]:
    """加载 executor.yaml；失败时返回空字典，避免沙箱构造硬失败。"""
    candidates: list[Path] = []
    env_path = os.environ.get("HARNESS_EXECUTOR_CONFIG")
    if env_path:
        candidates.append(Path(env_path))
    candidates.append(Path.cwd() / "config" / "executor.yaml")

    for path in candidates:
        if path.exists():
            try:
                raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                if isinstance(raw, dict):
                    return raw
            except Exception:
                break
    return {}


def default_sandbox_config() -> SandboxConfig:
    """读取 config/executor.yaml 中的 sandbox 默认配置。"""
    cfg = _load_executor_yaml()
    return SandboxConfig.from_dict(cfg.get("sandbox"))


class SandboxExecutor(ABC):
    """沙箱执行器抽象基类，实现 VerifyExecutor 协议。

    子类只需实现 ``run()``；通用参数与校验由基类负责。
    """

    def __init__(
        self,
        image: str | None = None,
        timeout: float | None = None,
        network: bool | None = None,
        memory: str | None = None,
        cpu: float | None = None,
        capabilities: CapabilitySet | Iterable[str] | None = None,
    ):
        self.config = default_sandbox_config()
        if image is not None:
            self.config.image = image
        if timeout is not None:
            self.config.timeout = timeout
        if network is not None:
            self.config.network = network
        if memory is not None:
            self.config.memory = memory
        if cpu is not None:
            self.config.cpu = cpu
        if capabilities is not None:
            self.config.capabilities = (
                capabilities
                if isinstance(capabilities, CapabilitySet)
                else CapabilitySet(capabilities)
            )
        self._validate_config()
        self._validate_capabilities()

    def _validate_config(self) -> None:
        """校验通用沙箱参数。"""
        if not self.config.image:
            raise SandboxConfigError("sandbox image must not be empty")
        if self.config.timeout <= 0:
            raise SandboxConfigError("sandbox timeout must be positive")
        if not self.config.memory:
            raise SandboxConfigError("sandbox memory must not be empty")
        if self.config.cpu <= 0:
            raise SandboxConfigError("sandbox cpu must be positive")

    def _validate_capabilities(self) -> None:
        """校验能力集与沙箱参数的兼容性。"""
        caps = self.config.capabilities
        if Capability.sudo in caps:
            raise SandboxConfigError(
                "sudo capability is prohibited inside sandbox"
            )
        if self.config.network and Capability.network not in caps:
            import warnings

            warnings.warn(
                "network capability missing but network=True requested; "
                "downgrading to network=none",
                stacklevel=2,
            )

    @abstractmethod
    async def run(
        self,
        cmd: str,
        cwd: str | None = None,
        session_id: str | None = None,
    ) -> ExecutionResult:
        """在沙箱内执行命令并返回结果。"""

    def supports(self, cmd: str) -> bool:
        return True

    def describe(self) -> str:
        return (
            f"{self.__class__.__name__} ("
            f"image={self.config.image}, "
            f"network={self.config.network}, "
            f"capabilities={self.config.capabilities.to_list()}"
            f")"
        )
