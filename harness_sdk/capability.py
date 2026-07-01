"""Harness SDK · 沙箱能力模型（v0.9.4）

能力（capability）是沙箱执行器与安全策略之间的显式契约。
``CapabilitySet`` 描述一次执行被允许使用的权限，``CommandRisk`` 描述
命令在已授予能力下的风险等级。
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import Enum
from typing import Any


class Capability(str, Enum):
    """沙箱能力项。

    每项能力对应一组可被授予或被沙箱限制的权限。
    """

    read = "read"  #: 读取文件系统 / 当前目录
    write = "write"  #: 写入文件系统（含重定向、rm、mv、cp）
    execute = "execute"  #: 执行任意命令（基础能力）
    network = "network"  #: 访问网络
    shell = "shell"  #: 使用 shell 元字符（管道、逻辑组合、子命令等）
    env = "env"  #: 读取/设置环境变量
    sudo = "sudo"  #: 提权（sudo / su）


class CommandRisk(str, Enum):
    """命令风险等级。

    由命令所需能力与已授予能力的对比，以及命令本身的危险特征共同决定。
    """

    safe = "safe"  #: 所需能力均已授予且无危险特征
    restricted = "restricted"  #: 能力已授予，但包含 shell/env 等需要额外关注的特征
    dangerous = "dangerous"  #: 涉及 write / network / sudo 等高危能力且已授予
    blocked = "blocked"  #: 缺少必需能力，或命中明确禁止前缀


#: 默认授予的能力集：允许读取与执行基础命令，默认禁用写、网络、shell、env、sudo。
DEFAULT_CAPABILITIES: list[Capability] = [Capability.read, Capability.execute]

#: 需要显式声明才允许使用的高危能力。
PRIVILEGED_CAPABILITIES: list[Capability] = [
    Capability.write,
    Capability.network,
    Capability.sudo,
]

#: 默认危险命令前缀到所需能力的映射。
DANGEROUS_PREFIX_CAPABILITIES: dict[str, Capability] = {
    "rm": Capability.write,
    "mv": Capability.write,
    "cp": Capability.write,
    "chmod": Capability.write,
    "chown": Capability.write,
    "curl": Capability.network,
    "wget": Capability.network,
    "ssh": Capability.network,
    "scp": Capability.network,
    "sudo": Capability.sudo,
    "su": Capability.sudo,
    "eval": Capability.shell,
    "exec": Capability.shell,
    "source": Capability.shell,
    ". ": Capability.shell,
}

#: shell 元字符 / 子串到所需 shell 能力的映射。
SHELL_METACHARACTER_CAPABILITIES: dict[str, Capability] = {
    "$(": Capability.shell,
    "${": Capability.shell,
    "&&": Capability.shell,
    "||": Capability.shell,
    ">>": Capability.shell,
    "`": Capability.shell,
    ";": Capability.shell,
    "|": Capability.shell,
    ">": Capability.write,
    "<": Capability.read,
    "*": Capability.shell,
    "?": Capability.shell,
}

#: 读取环境变量所需能力。
ENV_METACHARACTERS: list[str] = ["$", "export ", "env "]


class CapabilitySet:
    """能力集合。

    支持从字符串、``Capability``、可迭代对象构造，并提供集合运算、
    Pydantic 校验与序列化支持。
    """

    def __init__(self, capabilities: Iterable[Capability | str] | None = None):
        self._caps: set[Capability] = set()
        if capabilities is not None:
            for c in capabilities:
                self.add(c)

    def add(self, capability: Capability | str) -> None:
        """添加一项能力。"""
        self._caps.add(Capability(capability))

    def discard(self, capability: Capability | str) -> None:
        """移除一项能力（不存在时不报错）。"""
        self._caps.discard(Capability(capability))

    def __contains__(self, capability: Capability | str) -> bool:
        return Capability(capability) in self._caps

    def __iter__(self):
        return iter(self._caps)

    def __or__(self, other: CapabilitySet) -> CapabilitySet:
        return CapabilitySet(self._caps | other._caps)

    def __and__(self, other: CapabilitySet) -> CapabilitySet:
        return CapabilitySet(self._caps & other._caps)

    def __sub__(self, other: CapabilitySet) -> CapabilitySet:
        return CapabilitySet(self._caps - other._caps)

    def __len__(self) -> int:
        return len(self._caps)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CapabilitySet):
            return NotImplemented
        return self._caps == other._caps

    def __repr__(self) -> str:
        return f"CapabilitySet({sorted(self.to_list())!r})"

    def issubset(self, other: CapabilitySet) -> bool:
        """当前集合是否为 ``other`` 的子集。"""
        return self._caps.issubset(other._caps)

    def to_list(self) -> list[str]:
        """返回按字母序排列的能力字符串列表。"""
        return sorted(c.value for c in self._caps)

    def to_set(self) -> set[Capability]:
        """返回底层 ``Capability`` 集合的副本。"""
        return set(self._caps)

    @classmethod
    def default(cls) -> CapabilitySet:
        """返回默认能力集。"""
        return cls(DEFAULT_CAPABILITIES)

    @classmethod
    def all(cls) -> CapabilitySet:
        """返回全部能力。"""
        return cls(Capability)

    @classmethod
    def from_strings(cls, values: Iterable[str]) -> CapabilitySet:
        """从字符串列表构造能力集。"""
        return cls(values)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> Any:
        from pydantic_core import core_schema

        return core_schema.no_info_plain_validator_function(
            cls._validate,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda v: v.to_list(),
                return_schema=core_schema.list_schema(core_schema.str_schema()),
            ),
        )

    @classmethod
    def _validate(cls, value: Any) -> CapabilitySet:
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            return cls([value])
        if isinstance(value, dict):
            if "capabilities" in value:
                return cls(value["capabilities"])
            raise ValueError(f"invalid capability set mapping: {value!r}")
        if isinstance(value, Iterable):
            return cls(value)
        raise ValueError(f"invalid capability set: {value!r}")


def infer_capabilities_from_command(cmd: str) -> CapabilitySet:
    """根据命令字符串推断所需能力集合。

    推断规则：
    - 所有命令都需要 ``execute``
    - 读取类命令（cat/ls/pwd/git status...）额外需要 ``read``
    - 含 ``>``、``>>``、``rm``、``mv``、``cp`` 等需要 ``write``
    - 含 ``curl``、``wget``、``ssh``、``scp`` 等需要 ``network``
    - 含 ``|``、``&&``、``||``、``;``、``$(`` 等需要 ``shell``
    - 含 ``$VAR``、``export``、``env`` 等需要 ``env``
    - 含 ``sudo``/``su`` 需要 ``sudo``
    """
    required = CapabilitySet([Capability.execute])
    stripped = cmd.lstrip()
    lowered = stripped.lower()

    # 默认读取类命令需要 read
    read_prefixes = ("cat ", "ls", "pwd", "git status", "git diff", "git log",
                     "echo ", "pytest", "python -m pytest", "python -m harness_probe.cli")
    if any(lowered.startswith(p) for p in read_prefixes):
        required.add(Capability.read)

    # 危险前缀映射
    for prefix, cap in DANGEROUS_PREFIX_CAPABILITIES.items():
        if lowered.startswith(prefix.lower()):
            required.add(cap)

    # shell / env 元字符
    for token, cap in SHELL_METACHARACTER_CAPABILITIES.items():
        if token in cmd:
            required.add(cap)

    for token in ENV_METACHARACTERS:
        if token in cmd:
            required.add(Capability.env)

    return required


def evaluate_command_risk(
    cmd: str,
    granted: CapabilitySet | Iterable[str] | None = None,
) -> tuple[CommandRisk, CapabilitySet, CapabilitySet, str | None]:
    """评估命令在已授予能力下的风险等级。

    返回 ``(risk, required, missing, reason)``：
    - ``risk``: 风险等级
    - ``required``: 命令所需能力集
    - ``missing``: 缺少的能力集
    - ``reason``: 风险判定原因（字符串）
    """
    if granted is None:
        granted = CapabilitySet.default()
    elif not isinstance(granted, CapabilitySet):
        granted = CapabilitySet(granted)

    required = infer_capabilities_from_command(cmd)
    missing = required - granted

    if missing:
        return (
            CommandRisk.blocked,
            required,
            missing,
            f"missing_capabilities: {missing.to_list()}",
        )

    # 命中明确禁止前缀 -> blocked（即使能力已授予，也视为禁止在沙箱内执行）
    for prefix in ("sudo", "su"):
        if cmd.lstrip().lower().startswith(prefix):
            return (
                CommandRisk.blocked,
                required,
                CapabilitySet(),
                f"privileged_command_prohibited_in_sandbox: {prefix}",
            )

    required_values = required.to_set()

    if required_values & {Capability.write, Capability.network, Capability.sudo}:
        return (
            CommandRisk.dangerous,
            required,
            CapabilitySet(),
            f"dangerous_capabilities_used: {(required & CapabilitySet(PRIVILEGED_CAPABILITIES)).to_list()}",
        )

    if required_values & {Capability.shell, Capability.env}:
        return (
            CommandRisk.restricted,
            required,
            CapabilitySet(),
            f"restricted_capabilities_used: {(required & CapabilitySet([Capability.shell, Capability.env])).to_list()}",
        )

    return (
        CommandRisk.safe,
        required,
        CapabilitySet(),
        None,
    )


def describe_capability_requirements(cmd: str) -> dict[str, Any]:
    """返回命令能力需求的结构化描述（用于 CLI show / evaluate）。"""
    required = infer_capabilities_from_command(cmd)
    risk, required, missing, reason = evaluate_command_risk(cmd)
    return {
        "cmd": cmd,
        "required_capabilities": required.to_list(),
        "risk": risk.value,
        "missing_capabilities": missing.to_list(),
        "reason": reason,
    }
