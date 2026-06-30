"""Harness SDK · 命令安全校验（v0.7）"""

from __future__ import annotations

import os
import warnings
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class SafetyMode(str, Enum):
    """安全执行模式。"""

    whitelist = "whitelist"
    audit = "audit"
    unsafe = "unsafe"


class SafetyConfigError(Exception):
    """安全策略配置错误。"""


@dataclass
class SafetyResult:
    """单次命令安全校验结果。"""

    allowed: bool
    reason: str | None = None
    mode: SafetyMode = SafetyMode.whitelist


@dataclass
class SafetyConfig:
    """CommandSafetyChecker 配置。"""

    mode: SafetyMode = SafetyMode.whitelist
    allowed_commands: list[str] = field(default_factory=lambda: DEFAULT_ALLOWED_COMMANDS)
    dangerous_metacharacters: list[str] = field(
        default_factory=lambda: DEFAULT_DANGEROUS_METACHARACTERS
    )
    dangerous_prefixes: list[str] = field(default_factory=lambda: DEFAULT_DANGEROUS_PREFIXES)
    max_command_length: int = 1024
    unsafe_env_name: str = "HARNESS_UNSAFE"
    unsafe_env_value: str = "1"


# 默认允许的白名单命令（前缀匹配）。
# 包含 `pytest` 与 `python -m pytest` 两种写法，以兼容 v0.6 示例 task。
DEFAULT_ALLOWED_COMMANDS: list[str] = [
    "python -m pytest",
    "python -m harness_probe.cli",
    "pytest",
    "echo",
    "cat",
    "ls",
    "pwd",
    "git status",
    "git diff",
    "git log",
]

# 默认危险 shell 元字符/子串黑名单（不可覆盖）。
# 较长子串优先，确保报错原因更精确。
DEFAULT_DANGEROUS_METACHARACTERS: list[str] = [
    "$()",
    "${}",
    "&&",
    "||",
    ">>",
    "`",
    ";",
    "|",
    ">",
    "<",
    "*",
    "?",
]

# 默认危险命令前缀黑名单（不可覆盖）。
DEFAULT_DANGEROUS_PREFIXES: list[str] = [
    "rm",
    "mv",
    "cp",
    "sudo",
    "su",
    "chmod",
    "chown",
    "curl",
    "wget",
    "ssh",
    "scp",
    "eval",
    "exec",
    "source",
    ". ",
]


def load_safety_config(path: str | Path) -> SafetyConfig:
    """从 YAML 文件加载安全策略配置。

    合并规则：
    - allowed_commands：项目配置追加到默认列表
    - dangerous_metacharacters / dangerous_prefixes：项目配置追加到默认列表
    - 危险前缀不可被删除或覆盖；如果项目配置尝试覆盖，打印警告并忽略
    """
    config_path = Path(path)
    if not config_path.exists():
        warnings.warn(f"safety_config_not_found: {config_path}", stacklevel=2)
        return SafetyConfig()

    import yaml

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise SafetyConfigError(f"invalid_safety_yaml: {exc}") from exc

    if not isinstance(raw, dict):
        raise SafetyConfigError("safety_yaml_root_must_be_mapping")

    mode = raw.get("mode", "whitelist")
    try:
        mode = SafetyMode(mode)
    except ValueError as exc:
        raise SafetyConfigError(f"invalid_safety_mode: {mode}") from exc

    allowed_commands = list(DEFAULT_ALLOWED_COMMANDS)
    dangerous_metacharacters = list(DEFAULT_DANGEROUS_METACHARACTERS)
    dangerous_prefixes = list(DEFAULT_DANGEROUS_PREFIXES)

    user_allowed = raw.get("allowed_commands", [])
    if user_allowed:
        allowed_commands.extend([str(c) for c in user_allowed])

    user_meta = raw.get("dangerous_metacharacters", [])
    if user_meta:
        dangerous_metacharacters.extend([str(c) for c in user_meta])

    user_prefixes = raw.get("dangerous_prefixes", [])
    if user_prefixes:
        for prefix in user_prefixes:
            prefix = str(prefix)
            if prefix.lower() in {p.lower() for p in DEFAULT_DANGEROUS_PREFIXES}:
                warnings.warn(
                    f"dangerous_prefix_override_ignored: {prefix!r} cannot override defaults",
                    stacklevel=2,
                )
                continue
            dangerous_prefixes.append(prefix)

    max_command_length = raw.get("max_command_length", 1024)
    if not isinstance(max_command_length, int) or max_command_length <= 0:
        raise SafetyConfigError("max_command_length_must_be_positive_int")

    return SafetyConfig(
        mode=mode,
        allowed_commands=allowed_commands,
        dangerous_metacharacters=dangerous_metacharacters,
        dangerous_prefixes=dangerous_prefixes,
        max_command_length=max_command_length,
        unsafe_env_name=str(raw.get("unsafe_env_name", "HARNESS_UNSAFE")),
        unsafe_env_value=str(raw.get("unsafe_env_value", "1")),
    )


class CommandSafetyChecker:
    """基于白名单 + 黑名单的简单命令安全校验器。

    不做命令语义级分析，仅做前缀与子串匹配。
    """

    def __init__(self, config: SafetyConfig | None = None):
        self.config = config or SafetyConfig()

    def check(self, cmd: str) -> SafetyResult:
        mode = self.config.mode

        if mode == SafetyMode.unsafe:
            if not self._unsafe_confirmed():
                return SafetyResult(
                    allowed=False,
                    reason="unsafe_mode_not_confirmed: set HARNESS_UNSAFE=1",
                    mode=mode,
                )
            return SafetyResult(allowed=True, reason=None, mode=mode)

        reason = self._check_violations(cmd)
        if reason:
            return SafetyResult(allowed=False, reason=reason, mode=mode)
        return SafetyResult(allowed=True, reason=None, mode=mode)

    def _unsafe_confirmed(self) -> bool:
        return os.environ.get(self.config.unsafe_env_name) == self.config.unsafe_env_value

    def _check_violations(self, cmd: str) -> str | None:
        if len(cmd) > self.config.max_command_length:
            return (
                f"command_too_long: {len(cmd)} > {self.config.max_command_length}. "
                "Shorten the command or increase max_command_length in config/safety.yaml"
            )

        for token in self.config.dangerous_metacharacters:
            if token in cmd:
                return (
                    f"dangerous_metacharacter: {token!r}. "
                    "Remove shell metacharacters or use --safety-mode audit"
                )

        stripped = cmd.lstrip()
        lowered = stripped.lower()
        for prefix in self.config.dangerous_prefixes:
            if lowered.startswith(prefix.lower()):
                return (
                    f"dangerous_command_prefix: {prefix!r}. "
                    "Use a safer command or set HARNESS_UNSAFE=1 with --safety-mode unsafe"
                )

        if self.config.mode == SafetyMode.whitelist:
            if not any(stripped.startswith(allowed) for allowed in self.config.allowed_commands):
                return (
                    "not_in_whitelist. "
                    "To allow this command, update config/safety.yaml or use --safety-mode audit"
                )

        return None
