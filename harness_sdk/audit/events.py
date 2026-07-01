"""审计事件模型"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class AuditEvent(BaseModel):
    """审计事件基类。"""

    event_type: str
    run_id: str
    task: str
    hat: str | None = None
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_log_line(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_log_line(cls, line: str) -> "AuditEvent":
        data: dict[str, Any] = cls.model_validate_json(line).model_dump()
        event_type = data.get("event_type", "")
        if event_type == "run":
            return RunEvent.model_validate_json(line)
        if event_type == "verify":
            return VerifyEvent.model_validate_json(line)
        if event_type == "compile":
            return CompileEvent.model_validate_json(line)
        return cls.model_validate_json(line)


class RunEvent(AuditEvent):
    """一次 run 命令的执行审计事件。"""

    event_type: Literal["run"] = "run"
    executor_plugin: str | None = None
    commands: list[str] = Field(default_factory=list)
    result: str = ""  # done / blocked / aborted / error
    duration_ms: int = 0


class VerifyEvent(AuditEvent):
    """一次 verify 命令的审计事件。"""

    event_type: Literal["verify"] = "verify"
    verifier: str = ""  # PRE_SPAWN_VERIFY 或插件名
    result: str = ""  # pass / fail


class CompileEvent(AuditEvent):
    """一次 compile 命令的审计事件。"""

    event_type: Literal["compile"] = "compile"
    output: str = ""  # 输出摘要或产物路径


__all__ = ["AuditEvent", "CompileEvent", "RunEvent", "VerifyEvent"]
