"""Harness SDK · 审计日志（v0.9.2）

基于配置中心 ``harness.audit`` 段写入 JSONL 审计日志，并支持按文件数/天数保留。
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from harness_sdk.config import ConfigManager


@dataclass
class AuditEvent:
    """单次审计事件。"""

    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    session_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "session_id": self.session_id,
            "payload": self.payload,
        }


class AuditLogger:
    """审计日志写入器。

    从配置中心读取 ``harness.audit.log_dir`` 与 ``harness.audit.retention``。
    """

    def __init__(self, config: ConfigManager | None = None):
        self.config = config or ConfigManager.default()
        self._log_dir: Path | None = self.config.get_path("harness.audit.log_dir")
        self._retention = self.config.get("harness.audit.retention", {})

    @property
    def log_dir(self) -> Path | None:
        return self._log_dir

    def log(self, event: AuditEvent) -> Path:
        """写入一条审计事件并返回落盘路径。"""
        if self._log_dir is None:
            raise RuntimeError("audit.log_dir is not configured")
        self._log_dir.mkdir(parents=True, exist_ok=True)
        log_path = self._log_dir / f"audit_log_{event.session_id or 'default'}.jsonl"
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        self._apply_retention()
        return log_path

    def _apply_retention(self) -> None:
        if self._log_dir is None:
            return
        max_files = self._retention.get("max_files")
        max_days = self._retention.get("max_days")
        if max_files is None and max_days is None:
            return

        files = [
            p
            for p in self._log_dir.iterdir()
            if p.is_file() and p.suffix == ".jsonl"
        ]
        files.sort(key=lambda p: p.stat().st_mtime)

        now = time.time()
        days_sec = (max_days * 86400) if max_days else None

        for p in files:
            remove = False
            if days_sec is not None and (now - p.stat().st_mtime) > days_sec:
                remove = True
            if not remove and max_files is not None and len(files) > max_files:
                remove = True
            if remove:
                try:
                    p.unlink()
                    files.remove(p)
                except OSError:
                    pass
