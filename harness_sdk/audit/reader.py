"""审计日志读取器"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from harness_sdk.audit.events import AuditEvent, RunEvent
from harness_sdk.audit.retention import record_corrupt_line


class AuditReader:
    """审计日志读取器。"""

    def __init__(self, log_dir: Path | str | None = None) -> None:
        if log_dir is not None:
            self.log_dir = Path(log_dir)
        else:
            self.log_dir = self._default_log_dir()

    @staticmethod
    def _default_log_dir() -> Path:
        from harness_sdk.audit.logger import _resolve_log_dir
        from harness_sdk.config import ConfigManager

        return _resolve_log_dir(ConfigManager.default())

    def _iter_events(self) -> Any:
        if not self.log_dir.exists():
            return
        for path in sorted(
            self.log_dir.glob("audit_*.jsonl"),
            key=lambda p: p.stat().st_mtime,
        ):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            for raw_line in text.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    yield AuditEvent.from_log_line(line)
                except Exception as exc:  # noqa: BLE001
                    record_corrupt_line(self.log_dir, line, str(exc))

    def list_runs(
        self,
        task: str | None = None,
        hat: str | None = None,
        since: datetime | str | None = None,
        executor_plugin: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """返回事件摘要列表，默认只包含 run 事件。"""
        since_dt = self._normalize_since(since)
        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        for event in self._iter_events():
            if not isinstance(event, RunEvent):
                continue
            if task is not None and event.task != task:
                continue
            if hat is not None and event.hat != hat:
                continue
            if since_dt is not None:
                ev_time = self._parse_time(event.timestamp)
                if ev_time is None or ev_time < since_dt:
                    continue
            if executor_plugin is not None and event.executor_plugin != executor_plugin:
                continue
            if event.run_id in seen:
                continue
            seen.add(event.run_id)
            results.append(
                {
                    "run_id": event.run_id,
                    "task": event.task,
                    "hat": event.hat,
                    "result": event.result,
                    "timestamp": event.timestamp,
                    "executor_plugin": event.executor_plugin,
                    "duration_ms": event.duration_ms,
                }
            )
            if len(results) >= limit:
                break
        return results

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        """返回单个 run_id 的所有事件详情。"""
        path = self.log_dir / f"audit_{run_id}.jsonl"
        if not path.exists():
            return None
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return None

        events: list[dict[str, Any]] = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                event = AuditEvent.from_log_line(line)
                events.append(event.model_dump())
            except Exception as exc:  # noqa: BLE001
                record_corrupt_line(self.log_dir, line, str(exc))

        if not events:
            return None
        return {
            "run_id": run_id,
            "events": events,
        }

    def search(
        self,
        *,
        task: str | None = None,
        hat: str | None = None,
        event_type: str | None = None,
        since: datetime | str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """按条件搜索审计事件。"""
        since_dt = self._normalize_since(since)
        results: list[dict[str, Any]] = []
        for event in self._iter_events():
            if task is not None and event.task != task:
                continue
            if hat is not None and event.hat != hat:
                continue
            if event_type is not None and event.event_type != event_type:
                continue
            if since_dt is not None:
                ev_time = self._parse_time(event.timestamp)
                if ev_time is None or ev_time < since_dt:
                    continue
            results.append(event.model_dump())
            if len(results) >= limit:
                break
        return results

    @staticmethod
    def _normalize_since(since: datetime | str | None) -> datetime | None:
        if since is None:
            return None
        if isinstance(since, datetime):
            return since
        if isinstance(since, str):
            since = since.strip()
            # 相对时间：1d, 7d, 30d
            if since.endswith(("d", "D")) and since[:-1].isdigit():
                days = int(since[:-1])
                return datetime.now(timezone.utc) - timedelta(days=days)
            try:
                dt = datetime.fromisoformat(since)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                return None
        return None

    @staticmethod
    def _parse_time(ts: str) -> datetime | None:
        try:
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return None


__all__ = ["AuditReader"]
