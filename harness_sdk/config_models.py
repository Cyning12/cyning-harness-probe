"""Harness SDK · 配置 Pydantic 模型（v0.9.5）

为 ``ConfigManager`` 提供可验证的 Schema 模型。
所有字段默认与 ``harness_sdk/config.py`` 的 DEFAULTS 保持一致。
代码与文档语言：英文代码，中文注释。
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SafetyMode(str, Enum):
    """安全策略运行模式。"""

    whitelist = "whitelist"
    audit = "audit"
    unsafe = "unsafe"


class SandboxConfig(BaseModel):
    """沙箱执行器公共参数。"""

    model_config = ConfigDict(validate_assignment=True)

    image: str = "python:3.11-slim"
    timeout: float = Field(default=60.0, gt=0)
    network: bool = False
    memory: str = "512m"
    cpu: float = Field(default=1.0, gt=0)


class ExecutorConfig(BaseModel):
    """执行器插件与沙箱配置。"""

    model_config = ConfigDict(validate_assignment=True)

    default_plugin: str = "subprocess"
    plugins: dict[str, str] = Field(default_factory=dict)
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)

    @field_validator("plugins")
    @classmethod
    def _validate_plugins(cls, value: dict[str, str]) -> dict[str, str]:
        """校验每个插件路径符合 package.module:ClassName 格式。"""
        for name, path in value.items():
            if not _is_plugin_path(path):
                raise ValueError(f"plugin path {name}={path!r} must be 'package.module:ClassName'")
        return value


class RetentionConfig(BaseModel):
    """审计日志保留策略。"""

    model_config = ConfigDict(validate_assignment=True)

    max_files: int = Field(default=100, gt=0)
    max_days: int = Field(default=30, gt=0)

    # Pydantic v2 在 str 输入时会自动尝试转换，需显式拒绝以保持向后兼容
    @field_validator("max_files", "max_days", mode="before")
    @classmethod
    def _validate_int(cls, value: Any) -> Any:
        """保留整数字段严格校验，拒绝字符串数字。"""
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"must be int, got {type(value).__name__}")
        return value


class AuditConfig(BaseModel):
    """审计日志配置。"""

    model_config = ConfigDict(validate_assignment=True)

    log_dir: str = "~/.harness_probe/audit"
    retention: RetentionConfig = Field(default_factory=RetentionConfig)


class SafetyRefConfig(BaseModel):
    """安全策略引用配置（Safety 独立配置文件的引用）。"""

    model_config = ConfigDict(validate_assignment=True)

    mode: SafetyMode = SafetyMode.whitelist
    config_path: str = "config/safety.yaml"


class HarnessConfig(BaseModel):
    """顶层聚合配置。"""

    model_config = ConfigDict(validate_assignment=True)

    executor: ExecutorConfig = Field(default_factory=ExecutorConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)
    safety: SafetyRefConfig = Field(default_factory=SafetyRefConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HarnessConfig":
        """从字典构造，忽略未知字段，失败时抛出 ValidationError。"""
        return cls.model_validate(data)

    def to_dict(self) -> dict[str, Any]:
        """导出为可 JSON 序列化的字典。"""
        return self.model_dump(mode="json")


def _is_plugin_path(value: str) -> bool:
    """校验插件路径格式：``package.module:ClassName``。

    允许嵌套包（如 ``harness_sdk.executor_plugins.dry_run:DryRunExecutor``），
    类名须符合 Python 标识符规范。
    """
    if not isinstance(value, str):
        return False
    if ":" not in value:
        return False
    module_part, class_part = value.rsplit(":", 1)
    if not module_part or not class_part:
        return False
    # module 须为点分合法标识符
    if not re.fullmatch(r"([a-zA-Z_][a-zA-Z0-9_]*\.)*[a-zA-Z_][a-zA-Z0-9_]*", module_part):
        return False
    # class 须为合法标识符
    if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", class_part):
        return False
    return True


def validate_plugin_path(value: str) -> str:
    """可被 ``ConfigManager`` 直接使用的插件路径字段校验器。"""
    if not _is_plugin_path(value):
        raise ValueError(f"plugin path {value!r} must be 'package.module:ClassName'")
    return value


#: 默认插件路径常量（与 config.py 的 DEFAULTS 保持一致）
DEFAULT_PLUGIN_PATHS: dict[str, str] = {
    "dry-run": "harness_sdk.executor_plugins.dry_run:DryRunExecutor",
    "preview": "harness_sdk.executor_plugins.preview:PreviewExecutor",
    "subprocess": "harness_sdk.executor_plugins.subprocess:SubprocessExecutor",
    "docker": "harness_sdk.executor_plugins.docker:DockerExecutor",
    "firejail": "harness_sdk.executor_plugins.firejail:FirejailExecutor",
}


def validate_config_dict(data: dict[str, Any]) -> list[str]:
    """使用 Pydantic 模型校验配置字典，返回人类可读错误列表。

    与 ``ConfigManager.validate()`` 保持兼容，返回 ``list[str]``。
    """
    try:
        HarnessConfig.from_dict(data)
    except Exception as exc:  # noqa: BLE001 — 统一转换为字符串列表
        return _format_validation_errors(exc)
    return []


def _format_validation_errors(exc: Any) -> list[str]:
    """将 Pydantic ValidationError 展开为带字段路径的错误字符串。"""
    # 优先调用 pydantic 原生错误展开
    if hasattr(exc, "errors"):
        errors: list[str] = []
        try:
            for err in exc.errors():
                loc = ".".join(str(part) for part in err.get("loc", []))
                msg = err.get("msg", "")
                errors.append(f"harness.{loc}: {msg}")
            return errors
        except Exception:  # noqa: BLE001 — 退化返回原始信息
            return [str(exc)]
    return [str(exc)]
