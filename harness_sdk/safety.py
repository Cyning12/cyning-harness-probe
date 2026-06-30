"""Harness SDK · 命令安全校验（v0.7）"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum


class SafetyMode(str, Enum):
    """安全执行模式。"""

    whitelist = "whitelist"
    audit = "audit"
    unsafe = "unsafe"


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
            return f"command_too_long: {len(cmd)} > {self.config.max_command_length}"

        for token in self.config.dangerous_metacharacters:
            if token in cmd:
                return f"dangerous_metacharacter: {token!r}"

        stripped = cmd.lstrip()
        lowered = stripped.lower()
        for prefix in self.config.dangerous_prefixes:
            if lowered.startswith(prefix.lower()):
                return f"dangerous_command_prefix: {prefix!r}"

        if self.config.mode == SafetyMode.whitelist:
            if not any(stripped.startswith(allowed) for allowed in self.config.allowed_commands):
                return "not_in_whitelist"

        return None
