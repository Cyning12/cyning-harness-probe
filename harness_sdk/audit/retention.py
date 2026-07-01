"""审计日志保留策略"""

from __future__ import annotations

import json
import time
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _parse_timestamp(ts: str) -> datetime:
    """解析 ISO 格式时间戳，失败时返回 epoch。"""
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)


def apply_retention(
    log_dir: Path,
    *,
    max_files: int | None = None,
    max_days: int | None = None,
    errors_dir: Path | None = None,
) -> None:
    """按数量与天数清理日志文件。

    清理失败时不抛出异常，仅发出警告；下次写入时重试。
    """
    try:
        files = sorted(
            (p for p in log_dir.iterdir() if p.is_file() and p.suffix == ".jsonl"),
            key=lambda p: p.stat().st_mtime,
        )
    except OSError as exc:
        warnings.warn(f"audit retention scan failed: {exc}", stacklevel=2)
        return

    now = datetime.now(timezone.utc)

    # 按天数删除
    if max_days is not None and max_days > 0:
        cutoff = now - timedelta(days=max_days)
        for path in files:
            try:
                mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
                if mtime < cutoff:
                    path.unlink()
            except OSError as exc:
                warnings.warn(f"audit retention delete failed: {path}: {exc}", stacklevel=2)

    # 按数量保留（保留最新的）
    if max_files is not None and max_files > 0:
        try:
            remaining = sorted(
                (p for p in log_dir.iterdir() if p.is_file() and p.suffix == ".jsonl"),
                key=lambda p: p.stat().st_mtime,
            )
        except OSError:
            return
        if len(remaining) > max_files:
            for path in remaining[: len(remaining) - max_files]:
                try:
                    path.unlink()
                except OSError as exc:
                    warnings.warn(f"audit retention delete failed: {path}: {exc}", stacklevel=2)


def record_corrupt_line(
    log_dir: Path,
    line: str,
    reason: str,
    *,
    errors_dir: Path | None = None,
) -> None:
    """将损坏的日志行记录到 .audit/errors 目录。"""
    target = errors_dir or log_dir / ".audit" / "errors"
    try:
        target.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        error_path = target / f"corrupt_{stamp}_{time.monotonic_ns()}.jsonl"
        error_path.write_text(
            f'{{"line": {json.dumps(line)}, "reason": {json.dumps(reason)}}}\n',
            encoding="utf-8",
        )
    except OSError:
        pass


__all__ = ["apply_retention", "record_corrupt_line"]
