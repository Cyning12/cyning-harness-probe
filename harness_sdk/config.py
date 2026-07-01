"""Harness SDK · 配置中心（v0.9.2）

统一加载 ``config/*.yaml``、环境变量 ``HARNESS_*`` 与 CLI 覆盖，按优先级合并：

    默认值 < 配置文件 < 环境变量 < 命令行参数

本模块是 SDK 中唯一被允许读取文件、访问环境变量的配置入口；
编译/运行核心仍保持无副作用。
"""

from __future__ import annotations

import os
import re
import warnings
from pathlib import Path
from typing import Any

import yaml


class ConfigError(Exception):
    """配置加载或校验错误；携带友好错误信息，不抛堆栈。"""


#: 内置默认配置
DEFAULTS: dict[str, Any] = {
    "harness": {
        "executor": {
            "default_plugin": "subprocess",
            "plugins": {
                "dry-run": "harness_sdk.executor_plugins.dry_run:DryRunExecutor",
                "preview": "harness_sdk.executor_plugins.preview:PreviewExecutor",
                "subprocess": "harness_sdk.executor_plugins.subprocess:SubprocessExecutor",
                "docker": "harness_sdk.executor_plugins.docker:DockerExecutor",
                "firejail": "harness_sdk.executor_plugins.firejail:FirejailExecutor",
            },
            "sandbox": {
                "image": "python:3.11-slim",
                "timeout": 60.0,
                "network": False,
                "memory": "512m",
                "cpu": 1.0,
            },
        },
        "audit": {
            "log_dir": "~/.harness_probe/audit",
            "retention": {
                "max_files": 100,
                "max_days": 30,
            },
        },
        "safety": {
            "mode": "whitelist",
            "config_path": "config/safety.yaml",
        },
    }
}

#: 文件名到默认命名空间的映射（兼容未包裹 ``harness:`` 的遗留配置）
_FILE_NAMESPACE: dict[str, str] = {
    "executor.yaml": "harness.executor",
    "audit.yaml": "harness.audit",
    "safety.yaml": "harness.safety",
}

#: 已知环境变量到点分路径的精确映射（保留 ``default_plugin`` 这类下划线键）
_ENV_KEY_MAP: dict[str, str] = {
    "HARNESS_EXECUTOR_DEFAULT_PLUGIN": "harness.executor.default_plugin",
    "HARNESS_EXECUTOR_PLUGIN": "harness.executor.default_plugin",  # 向后兼容
    "HARNESS_AUDIT_LOG_DIR": "harness.audit.log_dir",
    "HARNESS_AUDIT_RETENTION_MAX_FILES": "harness.audit.retention.max_files",
    "HARNESS_AUDIT_RETENTION_MAX_DAYS": "harness.audit.retention.max_days",
    "HARNESS_SAFETY_MODE": "harness.safety.mode",
    "HARNESS_SAFETY_CONFIG_PATH": "harness.safety.config_path",
}


class ConfigManager:
    """统一配置管理器。

    用法::

        cfg = ConfigManager.default()
        plugin = cfg.get("harness.executor.default_plugin")
        cfg.set("harness.executor.default_plugin", "docker")  # CLI 覆盖
    """

    def __init__(self, data: dict[str, Any] | None = None):
        self._data: dict[str, Any] = _deep_copy(data) if data is not None else {}
        self._project_root: Path = Path.cwd()

    @classmethod
    def default(
        cls,
        config_dir: str | Path | None = None,
        *,
        project_root: str | Path | None = None,
    ) -> "ConfigManager":
        """返回带默认值、配置文件、环境变量合并后的实例。

        ``config_dir`` 未提供时依次尝试 ``<project_root>/config``、``<cwd>/config``。
        """
        instance = cls(_deep_copy(DEFAULTS))
        instance._project_root = Path(project_root) if project_root else Path.cwd()

        cfg_dir = cls._resolve_config_dir(config_dir, instance._project_root)
        if cfg_dir is not None and cfg_dir.exists():
            instance._load_directory(cfg_dir)
        else:
            warnings.warn(f"config_dir_not_found: {cfg_dir}; using defaults", stacklevel=2)

        instance._apply_env_overrides()
        return instance

    # ------------------------------------------------------------------
    # 读取
    # ------------------------------------------------------------------
    def get(self, dotted_path: str, default: Any = None) -> Any:
        """按 ``harness.executor.default_plugin`` 形式读取配置。"""
        parts = dotted_path.split(".")
        node: Any = self._data
        for part in parts:
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def get_path(self, dotted_path: str, default: str | Path | None = None) -> Path | None:
        """读取路径类配置并解析 ``~`` / 相对路径为绝对路径。"""
        value = self.get(dotted_path, default)
        if value is None:
            return None
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = self._project_root / path
        return path.resolve()

    def set(self, dotted_path: str, value: Any) -> None:
        """设置配置，用于命令行参数覆盖（最高优先级）。"""
        parts = dotted_path.split(".")
        node = self._data
        for part in parts[:-1]:
            if part not in node or not isinstance(node[part], dict):
                node[part] = {}
            node = node[part]
        node[parts[-1]] = value

    def to_dict(self) -> dict[str, Any]:
        """返回当前合并后配置的深拷贝。"""
        return _deep_copy(self._data)

    # ------------------------------------------------------------------
    # 校验
    # ------------------------------------------------------------------
    def validate(self) -> list[str]:
        """校验配置类型，返回人类可读错误列表；空列表表示通过。"""
        errors: list[str] = []

        def _check_int(path: str) -> None:
            value = self.get(path)
            if value is None:
                return
            if not isinstance(value, int) or isinstance(value, bool):
                errors.append(f"{path} must be int, got {type(value).__name__}")

        def _check_float(path: str) -> None:
            value = self.get(path)
            if value is None:
                return
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                errors.append(f"{path} must be float, got {type(value).__name__}")

        def _check_bool(path: str) -> None:
            value = self.get(path)
            if value is None:
                return
            if not isinstance(value, bool):
                errors.append(f"{path} must be bool, got {type(value).__name__}")

        def _check_str(path: str, choices: list[str] | None = None) -> None:
            value = self.get(path)
            if value is None:
                return
            if not isinstance(value, str):
                errors.append(f"{path} must be str, got {type(value).__name__}")
                return
            if choices and value not in choices:
                errors.append(f"{path}={value!r} must be one of {choices}")

        def _check_positive_int(path: str) -> None:
            value = self.get(path)
            if value is None:
                return
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                errors.append(f"{path} must be positive int, got {value!r}")

        _check_str("harness.executor.default_plugin")
        plugins = self.get("harness.executor.plugins")
        if plugins is not None and not isinstance(plugins, dict):
            errors.append("harness.executor.plugins must be mapping")

        sandbox = self.get("harness.executor.sandbox")
        if sandbox is not None and not isinstance(sandbox, dict):
            errors.append("harness.executor.sandbox must be mapping")
        else:
            _check_float("harness.executor.sandbox.timeout")
            _check_bool("harness.executor.sandbox.network")
            _check_str("harness.executor.sandbox.memory")

        _check_str(
            "harness.safety.mode",
            choices=["whitelist", "audit", "unsafe"],
        )
        _check_str("harness.safety.config_path")

        _check_str("harness.audit.log_dir")
        retention = self.get("harness.audit.retention")
        if retention is not None and not isinstance(retention, dict):
            errors.append("harness.audit.retention must be mapping")
        else:
            _check_positive_int("harness.audit.retention.max_files")
            _check_positive_int("harness.audit.retention.max_days")

        return errors

    # ------------------------------------------------------------------
    # 加载与合并
    # ------------------------------------------------------------------
    @staticmethod
    def _resolve_config_dir(
        config_dir: str | Path | None,
        project_root: Path,
    ) -> Path | None:
        if config_dir is not None:
            return Path(config_dir).expanduser().resolve()
        candidate = project_root / "config"
        if candidate.exists():
            return candidate
        candidate = Path.cwd() / "config"
        if candidate.exists():
            return candidate
        return None

    def _load_directory(self, config_dir: Path) -> None:
        for yaml_path in sorted(config_dir.glob("*.yaml")):
            try:
                raw_text = yaml_path.read_text(encoding="utf-8")
                raw = yaml.safe_load(raw_text)
            except yaml.YAMLError as exc:
                raise ConfigError(
                    f"invalid_yaml: {yaml_path}\n  {exc}"
                ) from exc
            except OSError as exc:
                warnings.warn(
                    f"config_file_read_failed: {yaml_path}: {exc}",
                    stacklevel=2,
                )
                continue

            if raw is None:
                raw = {}
            if not isinstance(raw, dict):
                raise ConfigError(
                    f"config_root_must_be_mapping: {yaml_path}"
                )

            # 若文件顶层含 harness 键，直接合并；否则按文件名推断命名空间
            if "harness" in raw:
                self._merge(self._data, raw)
            else:
                namespace: str | None = None
                extracted = raw
                if yaml_path.name == "probe_config.yaml" and "probe" in raw:
                    # 兼容 v0.7 probe_config.yaml（顶层 probe: ...）
                    namespace = "harness.probe"
                    extracted = raw["probe"]
                elif yaml_path.name in _FILE_NAMESPACE:
                    namespace = _FILE_NAMESPACE[yaml_path.name]

                if namespace is not None:
                    self._merge_at_namespace(self._data, namespace, extracted)
                else:
                    # 未知配置文件直接放到顶层（保持可扩展）
                    self._merge(self._data, raw)

    def _apply_env_overrides(self) -> None:
        for key, value in os.environ.items():
            if not key.startswith("HARNESS_"):
                continue
            dotted = _ENV_KEY_MAP.get(key)
            if dotted is None:
                dotted = _env_key_to_dotted(key)
            converted = _convert_env_value(value)
            self.set(dotted, converted)

    @staticmethod
    def _merge(base: dict[str, Any], overlay: dict[str, Any]) -> None:
        for key, value in overlay.items():
            if (
                key in base
                and isinstance(base[key], dict)
                and isinstance(value, dict)
            ):
                ConfigManager._merge(base[key], value)
            else:
                base[key] = value

    @staticmethod
    def _merge_at_namespace(
        base: dict[str, Any],
        namespace: str,
        overlay: dict[str, Any],
    ) -> None:
        parts = namespace.split(".")
        node = base
        for part in parts:
            if part not in node or not isinstance(node[part], dict):
                node[part] = {}
            node = node[part]
        ConfigManager._merge(node, overlay)


def _deep_copy(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _deep_copy(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deep_copy(v) for v in obj]
    return obj


def _env_key_to_dotted(key: str) -> str:
    """HARNESS_EXECUTOR_DEFAULT_PLUGIN → harness.executor.default_plugin"""
    body = key[len("HARNESS_") :]
    return body.lower().replace("_", ".")


def _convert_env_value(value: str) -> Any:
    """尝试把环境变量字符串转成合理的 Python 类型。"""
    lowered = value.lower()
    if lowered in ("true", "yes", "1"):
        return True
    if lowered in ("false", "no", "0"):
        return False
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    return value
