"""审计日志记录器

v0.9.2 起读取 ``harness.audit`` 配置段，保留 v0.9.1 单例/内存回退/保留策略能力。
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path
from typing import Any

from harness_sdk.audit.events import AuditEvent
from harness_sdk.audit.retention import apply_retention
from harness_sdk.config import ConfigManager


def get_default_log_dir() -> Path:
    """返回默认审计日志目录 ~/.harness_probe/audit/。"""
    home = Path.home()
    return home / ".harness_probe" / "audit"


def _as_config_manager(config: ConfigManager | dict[str, Any] | None) -> ConfigManager:
    """兼容 v0.9.1 测试直接传入 audit 段字典，以及 v0.9.2 配置中心。"""
    if config is None:
        return ConfigManager.default()
    if isinstance(config, ConfigManager):
        return config
    if isinstance(config, dict) and "harness" not in config:
        return ConfigManager({"harness": {"audit": config}})
    return ConfigManager(config)


def _resolve_log_dir(config: ConfigManager) -> Path:
    """按优先级解析审计日志目录：

    1. 环境变量 HARNESS_AUDIT_LOG_DIR（保持 v0.9.1 兼容）
    2. 配置中心 harness.audit.log_dir
    3. 默认 ~/.harness_probe/audit
    """
    env_dir = os.environ.get("HARNESS_AUDIT_LOG_DIR")
    if env_dir:
        return Path(env_dir).expanduser()
    configured = config.get("harness.audit.log_dir")
    if configured:
        return Path(configured).expanduser()
    return get_default_log_dir()


class AuditLogger:
    """单例审计日志记录器。

    支持通过配置中心初始化，也保留 ``AuditLogger()`` 无参默认行为。
    """

    _instance: "AuditLogger | None" = None
    _initialized: bool

    def __new__(cls, *, config: ConfigManager | dict[str, Any] | None = None) -> "AuditLogger":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, *, config: ConfigManager | dict[str, Any] | None = None) -> None:
        if self._initialized:
            return
        self._config = _as_config_manager(config)
        self._log_dir = _resolve_log_dir(self._config)
        self._retention = self._config.get("harness.audit.retention", {})
        self._memory_buffer: list[str] = []
        self._initialized = True

    @classmethod
    def get_instance(cls, *, config: ConfigManager | dict[str, Any] | None = None) -> "AuditLogger":
        return cls(config=config)

    @classmethod
    def reset(cls) -> None:
        """重置单例（仅用于测试）。"""
        cls._instance = None

    @property
    def log_dir(self) -> Path:
        return self._log_dir

    def get_log_dir(self) -> Path:
        """v0.9.1 兼容别名。"""
        return self._log_dir

    def is_memory_fallback(self) -> bool:
        """当前是否处于内存回退模式。"""
        return bool(self._memory_buffer)

    def get_memory_logs(self) -> list[str]:
        """返回缓存的内存日志行。"""
        return self._memory_buffer.copy()

    def get_memory_buffer(self) -> list[str]:
        """返回因目录不可写而缓存的内存日志行（仅用于测试）。"""
        return self._memory_buffer.copy()

    def _ensure_dir(self) -> bool:
        try:
            self._log_dir.mkdir(parents=True, exist_ok=True)
            return True
        except OSError:
            warnings.warn(
                f"audit_log_dir_unwritable: {self._log_dir}; falling back to in-memory",
                stacklevel=2,
            )
            return False

    def log_event(self, event: AuditEvent) -> None:
        """追加事件到日志文件；不可写时保存到内存。"""
        line = event.to_log_line() + "\n"
        if self._ensure_dir():
            try:
                log_path = self._log_dir / f"audit_{getattr(event, 'run_id', 'default')}.jsonl"
                with log_path.open("a", encoding="utf-8") as f:
                    f.write(line)
                if self._memory_buffer:
                    with log_path.open("a", encoding="utf-8") as f:
                        f.writelines(self._memory_buffer)
                    self._memory_buffer.clear()
                apply_retention(self._log_dir, **self._retention)
            except OSError as exc:
                warnings.warn(
                    f"audit_log_write_failed: {self._log_dir / 'audit_*.jsonl'}: {exc}; falling back to in-memory",
                    stacklevel=2,
                )
                self._memory_buffer.append(line)
        else:
            self._memory_buffer.append(line)


def get_logger(config: ConfigManager | dict[str, Any] | None = None) -> AuditLogger:
    """便捷函数：返回 AuditLogger 单例。"""
    return AuditLogger.get_instance(config=config)
