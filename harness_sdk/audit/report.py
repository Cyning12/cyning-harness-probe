"""审计报告生成器"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from harness_sdk.audit.events import RunEvent
from harness_sdk.audit.reader import AuditReader


class AuditReport:
    """审计报告：支持 JSON / Markdown 输出与多维度过滤。"""

    def __init__(
        self,
        reader: AuditReader | None = None,
        *,
        task: str | None = None,
        hat: str | None = None,
        since: datetime | str | None = None,
    ) -> None:
        self.reader = reader or AuditReader()
        self.task = task
        self.hat = hat
        self.since = since

    def _collect_run_events(self) -> list[RunEvent]:
        events: list[RunEvent] = []
        for event in self.reader._iter_events():
            if not isinstance(event, RunEvent):
                continue
            if self.task is not None and event.task != self.task:
                continue
            if self.hat is not None and event.hat != self.hat:
                continue
            if self.since is not None:
                since_dt = self.reader._normalize_since(self.since)
                ev_time = self.reader._parse_time(event.timestamp)
                if since_dt is not None and ev_time is not None and ev_time < since_dt:
                    continue
            events.append(event)
        return events

    def to_json(self) -> str:
        """生成结构化 JSON 报告。"""
        events = self._collect_run_events()
        total = len(events)
        done = sum(1 for e in events if e.result == "done")
        blocked = sum(1 for e in events if e.result == "blocked")
        failed = sum(1 for e in events if e.result in {"error", "aborted"})
        total_duration_ms = sum(e.duration_ms for e in events)
        data = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "filters": {
                "task": self.task,
                "hat": self.hat,
                "since": self.since.isoformat() if isinstance(self.since, datetime) else self.since,
            },
            "summary": {
                "total_runs": total,
                "done": done,
                "blocked": blocked,
                "failed": failed,
                "total_duration_ms": total_duration_ms,
            },
            "runs": [e.model_dump() for e in events],
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    def to_markdown(self) -> str:
        """生成人类可读的 Markdown 报告。"""
        events = self._collect_run_events()
        total = len(events)
        done = sum(1 for e in events if e.result == "done")
        blocked = sum(1 for e in events if e.result == "blocked")
        failed = sum(1 for e in events if e.result in {"error", "aborted"})
        total_duration_ms = sum(e.duration_ms for e in events)

        lines = [
            "# Harness Probe · 审计报告",
            "",
            f"- **生成时间**: {datetime.now(timezone.utc).isoformat()}",
            f"- **过滤条件**: task={self.task or '全部'}, hat={self.hat or '全部'}, since={self._fmt_since()}",
            "",
            "## 汇总",
            "",
            "| 指标 | 数值 |",
            "|------|------|",
            f"| 总运行数 | {total} |",
            f"| 成功 | {done} |",
            f"| 阻塞 | {blocked} |",
            f"| 失败/异常 | {failed} |",
            f"| 总耗时 (ms) | {total_duration_ms} |",
            "",
            "## 运行明细",
            "",
            "| run_id | task | hat | executor_plugin | result | duration_ms | timestamp |",
            "|--------|------|-----|-----------------|--------|-------------|-----------|",
        ]
        for e in events:
            lines.append(
                f"| {e.run_id} | {e.task} | {e.hat or '-'} | "
                f"{e.executor_plugin or '-'} | {e.result} | {e.duration_ms} | {e.timestamp} |"
            )
        lines.append("")
        return "\n".join(lines)

    def _fmt_since(self) -> str:
        if self.since is None:
            return "全部"
        if isinstance(self.since, datetime):
            return self.since.isoformat()
        return str(self.since)

    def write(self, path: Path | str | None, *, fmt: str = "markdown") -> str:
        """生成报告内容；如提供 path 则写入文件。"""
        content = self.to_markdown() if fmt == "markdown" else self.to_json()
        if path is not None:
            p = Path(path)
            p.write_text(content, encoding="utf-8")
        return content


__all__ = ["AuditReport"]
