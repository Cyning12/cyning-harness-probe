"""Executor plugin loader."""

from __future__ import annotations

import importlib
import os
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from harness_sdk.executor_plugins.base import ExecutorPluginError
from harness_sdk.executor_plugins.subprocess import SubprocessExecutor

if TYPE_CHECKING:
    from harness_sdk.executor_plugins.base import VerifyExecutor


_BUILTIN_PLUGINS: dict[str, str] = {
    "dry-run": "harness_sdk.executor_plugins.dry_run:DryRunExecutor",
    "preview": "harness_sdk.executor_plugins.preview:PreviewExecutor",
    "subprocess": "harness_sdk.executor_plugins.subprocess:SubprocessExecutor",
    "docker": "harness_sdk.executor_plugins.docker:DockerExecutor",
    "firejail": "harness_sdk.executor_plugins.firejail:FirejailExecutor",
}


def _load_executor_config(path: Path | None) -> dict:
    """加载 executor YAML 配置；出错时返回空 dict。"""
    if path is None or not path.exists():
        return {}
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        warnings.warn(
            f"executor_config_load_failed: {exc}; using default subprocess",
            stacklevel=2,
        )
        return {}
    if not isinstance(raw, dict):
        warnings.warn(
            "executor_config_root_must_be_mapping; using default subprocess",
            stacklevel=2,
        )
        return {}
    return raw


def _resolve_plugin_class(spec: str) -> type:
    """解析 'module.path:ClassName' 并返回类对象。"""
    try:
        module_path, class_name = spec.split(":")
    except ValueError as exc:
        raise ExecutorPluginError(f"invalid_executor_plugin_spec: {spec!r}") from exc
    try:
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
    except Exception as exc:
        raise ExecutorPluginError(
            f"executor_plugin_load_failed: {spec!r}: {exc}"
        ) from exc
    return cls


def load_executor_plugin(
    name: str | None = None,
    *,
    config_path: str | Path | None = None,
    **plugin_kwargs: Any,
) -> VerifyExecutor:
    """按名称加载执行器插件。

    解析优先级：
      1. 显式传入的 name
      2. config/executor.yaml 中的 default_plugin
      3. 环境变量 HARNESS_EXECUTOR_PLUGIN
      4. 默认 subprocess

    ``**plugin_kwargs`` 会透传给插件构造函数，用于 CLI 覆盖沙箱默认参数。
    配置文件不存在时自动使用内置插件表；配置文件损坏时回退到
    默认 subprocess 并发出警告。
    """
    if config_path is None:
        candidate = Path.cwd() / "config" / "executor.yaml"
        if candidate.exists():
            config_path = candidate

    cfg = _load_executor_config(Path(config_path) if config_path else None)
    custom_plugins = cfg.get("plugins", {})
    if not isinstance(custom_plugins, dict):
        warnings.warn(
            "executor_config_plugins_must_be_mapping; using built-ins",
            stacklevel=2,
        )
        custom_plugins = {}

    plugins = {**_BUILTIN_PLUGINS, **custom_plugins}

    resolved_name = name
    if resolved_name is None:
        resolved_name = (
            cfg.get("default_plugin")
            or os.environ.get("HARNESS_EXECUTOR_PLUGIN")
            or "subprocess"
        )

    if resolved_name not in plugins:
        raise ExecutorPluginError(f"unknown_executor_plugin: {resolved_name!r}")

    spec = plugins[resolved_name]
    try:
        cls = _resolve_plugin_class(spec)
    except ExecutorPluginError as exc:
        # 配置指向的插件无法加载时回退默认 subprocess（仅当 name 来自配置且无额外构造参数时）
        if name is None and cfg.get("default_plugin") and not plugin_kwargs:
            warnings.warn(
                f"{exc}; falling back to default subprocess",
                stacklevel=2,
            )
            cls = SubprocessExecutor
        else:
            raise

    return cls(**plugin_kwargs)
