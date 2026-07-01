"""Harness SDK · 配置中心（v0.9.5）

统一加载 ``config/*.yaml``、环境变量 ``HARNESS_*`` 与 CLI 覆盖，按优先级合并：

    默认值 < 配置基础文件 < 环境配置文件 < 环境变量 < 命令行参数

本模块是 SDK 中唯一被允许读取文件、访问环境变量的配置入口；
编译/运行核心仍保持无副作用。
"""

from __future__ import annotations

import os
import re
import threading
import time
import warnings
from pathlib import Path
from typing import Any, Callable

import yaml

from harness_sdk.config_models import validate_config_dict


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

#: 轮询模式默认间隔（秒）
_POLL_INTERVAL = 1.0
#: 文件写入防抖（秒）
_DEBOUNCE = 0.5
#: 热重载仅监听这些扩展名
_WATCH_EXTENSIONS = {".yaml"}


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
        self._config_dir: Path | None = None
        self._env: str = "dev"
        self._on_reload: list[Callable[["ConfigManager"], None]] = []
        self._watch_running: bool = False
        self._watch_thread: threading.Thread | None = None
        self._watch_lock = threading.Lock()
        self._watch_observers: list[Any] = []
        self._last_seen: dict[Path, float] = {}

    @classmethod
    def default(
        cls,
        config_dir: str | Path | None = None,
        *,
        env: str = "dev",
        project_root: str | Path | None = None,
    ) -> "ConfigManager":
        """返回带默认值、配置文件、环境变量合并后的实例。

        ``config_dir`` 未提供时依次尝试 ``<project_root>/config``、``<cwd>/config``。
        """
        instance = cls(_deep_copy(DEFAULTS))
        instance._env = env
        instance._project_root = Path(project_root) if project_root else Path.cwd()

        cfg_dir = cls._resolve_config_dir(config_dir, instance._project_root)
        if cfg_dir is not None and cfg_dir.exists():
            instance._config_dir = cfg_dir
            instance._load_directory(cfg_dir, env)
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
        """校验配置类型，返回人类可读错误列表；空列表表示通过。

        内部使用 Pydantic 模型，对外保持返回 ``list[str]`` 的兼容签名。
        """
        harness = self._data.get("harness")
        if not isinstance(harness, dict):
            return ["harness section must be a mapping"]
        return validate_config_dict(harness)

    # ------------------------------------------------------------------
    # 热重载
    # ------------------------------------------------------------------
    def register_on_reload(self, callback: Callable[["ConfigManager"], None]) -> None:
        """注册一个回调函数，在配置热重载完成后触发。"""
        self._on_reload.append(callback)

    def watch(self) -> "ConfigManager":
        """启动对 ``config_dir`` 下 ``.yaml`` 文件的热重载监听。

        返回 self，支持上下文管理器 ``with cfg.watch(): ...``。
        """
        if self._config_dir is None:
            warnings.warn("config_dir not set; watch() has no effect", stacklevel=2)
            return self
        with self._watch_lock:
            if self._watch_running:
                return self
            self._watch_running = True
            try:
                self._start_watchdog()
            except Exception as exc:  # noqa: BLE001 — 降级到轮询
                warnings.warn(
                    f"watchdog_start_failed: {exc}; falling back to polling",
                    UserWarning,
                    stacklevel=2,
                )
                self._start_polling()
        return self

    def stop_watch(self) -> "ConfigManager":
        """停止热重载监听。"""
        with self._watch_lock:
            self._watch_running = False
            self._stop_watchdog()
            if self._watch_thread is not None and self._watch_thread.is_alive():
                self._watch_thread.join(timeout=1.0)
                self._watch_thread = None
        return self

    def __enter__(self) -> "ConfigManager":
        self.watch()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.stop_watch()

    def _reload(self) -> None:
        """重新加载配置文件并触发回调。"""
        if self._config_dir is None:
            return
        new_data = _deep_copy(DEFAULTS)
        # 使用相同实例变量，重新加载目录
        self._data = new_data
        self._load_directory(self._config_dir, self._env)
        self._apply_env_overrides()
        for callback in self._on_reload:
            try:
                callback(self)
            except Exception as exc:  # noqa: BLE001 — 回调异常不应中断重载
                warnings.warn(f"reload_callback_failed: {exc}", UserWarning, stacklevel=2)

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

    def _load_directory(self, config_dir: Path, env: str) -> None:
        """多环境加载：基础文件 -> 环境文件 -> 合并到内部数据。"""
        yaml_files = sorted(config_dir.glob("*.yaml"))
        env_files = {p.name for p in yaml_files if self._is_env_file(p.name, env)}
        for path in yaml_files:
            if path.name in env_files:
                continue
            env_path = config_dir / f"{path.stem}.{env}.yaml"
            # 先推断基础文件的命名空间，环境文件使用相同命名空间
            base_ns = self._namespace_for_file(path.name)
            if env_path.exists():
                self._load_file(path, namespace=base_ns)
                self._load_file(env_path, namespace=base_ns)
            else:
                self._load_file(path, namespace=base_ns)

    def _is_env_file(self, name: str, env: str) -> bool:
        """判断文件名是否形如 ``<base>.<env>.yaml``。"""
        parts = name.rsplit(".", 2)
        if len(parts) != 3:
            return False
        return parts[2] == "yaml" and parts[1] == env

    def _namespace_for_file(self, name: str) -> str | None:
        """根据文件名返回应该合并到的命名空间。"""
        if name == "probe_config.yaml":
            return "harness.probe"
        return _FILE_NAMESPACE.get(name)

    def _load_file(self, yaml_path: Path, *, namespace: str | None = None) -> None:
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
            return

        if raw is None:
            raw = {}
        if not isinstance(raw, dict):
            raise ConfigError(
                f"config_root_must_be_mapping: {yaml_path}"
            )

        # 若显式指定了命名空间（用于环境文件），直接按该命名空间合并
        if namespace is not None:
            # probe_config.yaml 特殊处理：内容已包裹在 probe 键下
            if yaml_path.name == "probe_config.yaml" and "probe" in raw:
                self._merge_at_namespace(self._data, namespace, raw["probe"])
            else:
                self._merge_at_namespace(self._data, namespace, raw)
            return

        # 若文件顶层含 harness 键，直接合并；否则按文件名推断命名空间
        if "harness" in raw:
            self._merge(self._data, raw)
        else:
            extracted = raw
            if yaml_path.name == "probe_config.yaml" and "probe" in raw:
                # 兼容 v0.7 probe_config.yaml（顶层 probe: ...）
                namespace = "harness.probe"
                extracted = raw["probe"]
            elif yaml_path.name in _FILE_NAMESPACE:
                namespace = _FILE_NAMESPACE[yaml_path.name]
            else:
                namespace = None

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

    # ------------------------------------------------------------------
    # 监听实现
    # ------------------------------------------------------------------
    def _start_watchdog(self) -> None:
        """尝试使用 watchdog 启动文件系统监听；失败时抛出异常以便上层降级。"""
        if self._config_dir is None:
            return

        # 动态导入；未安装时会触发 ImportError，由 watch() 降级到轮询
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer

        class _ConfigHandler(FileSystemEventHandler):
            def __init__(self, manager: "ConfigManager") -> None:
                self._manager = manager
                self._last_reload = 0.0

            def on_modified(self, event: Any) -> None:
                if event.is_directory:
                    return
                self._maybe_reload(event.src_path)

            def on_created(self, event: Any) -> None:
                if event.is_directory:
                    return
                self._maybe_reload(event.src_path)

            def _maybe_reload(self, src_path: str) -> None:
                path = Path(src_path)
                if path.suffix not in _WATCH_EXTENSIONS:
                    return
                now = time.time()
                # 防抖
                if now - self._last_reload < _DEBOUNCE:
                    return
                self._last_reload = now
                self._manager._reload()

        observer = Observer()
        handler = _ConfigHandler(self)
        observer.schedule(handler, str(self._config_dir), recursive=False)
        observer.start()
        self._watch_observers.append(observer)

    def _stop_watchdog(self) -> None:
        for observer in self._watch_observers:
            try:
                observer.stop()
                observer.join(timeout=1.0)
            except Exception:  # noqa: BLE001 — 停止失败不影响主流程
                pass
        self._watch_observers.clear()

    def _start_polling(self) -> None:
        """watchdog 不可用时，使用轮询监听文件 mtime。"""
        if self._config_dir is None:
            return
        self._last_seen = self._snapshot_mtimes()

        def _poll_loop() -> None:
            while True:
                with self._watch_lock:
                    if not self._watch_running:
                        break
                time.sleep(_POLL_INTERVAL)
                snapshot = self._snapshot_mtimes()
                if snapshot != self._last_seen:
                    # 防抖：等待短暂时间再重载，避免读取半写文件
                    time.sleep(_DEBOUNCE)
                    self._last_seen = self._snapshot_mtimes()
                    self._reload()

        thread = threading.Thread(target=_poll_loop, daemon=True)
        thread.start()
        self._watch_thread = thread
        warnings.warn(
            "watchdog not installed; using polling fallback (1s) for config hot-reload",
            UserWarning,
            stacklevel=2,
        )

    def _snapshot_mtimes(self) -> dict[Path, float]:
        """返回当前 config 目录下所有 .yaml 文件的路径与 mtime 映射。"""
        if self._config_dir is None:
            return {}
        result: dict[Path, float] = {}
        for path in self._config_dir.glob("*.yaml"):
            try:
                result[path] = path.stat().st_mtime
            except OSError:
                continue
        return result


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
