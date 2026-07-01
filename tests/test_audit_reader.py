"""审计日志读取器测试"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from harness_sdk.audit import AuditLogger
from harness_sdk.audit.events import RunEvent, VerifyEvent
from harness_sdk.audit.reader import AuditReader


@pytest.fixture
def reader_with_logs(tmp_path):
    AuditLogger.reset()
    log_dir = tmp_path / "audit"
    logger = AuditLogger(config={"log_dir": str(log_dir)})

    # 创建一些事件
    logger.log_event(RunEvent(run_id="run-old", task="task-a.md", hat="30", result="done", duration_ms=10))
    logger.log_event(RunEvent(run_id="run-new", task="task-b.md", hat="40", result="blocked", duration_ms=20))
    logger.log_event(VerifyEvent(run_id="run-new", task="task-b.md", verifier="PRE_SPAWN_VERIFY", result="pass"))

    yield AuditReader(log_dir)
    AuditLogger.reset()


def test_list_runs_default(reader_with_logs: AuditReader):
    runs = reader_with_logs.list_runs()
    assert len(runs) == 2
    assert runs[0]["run_id"] == "run-old"
    assert runs[1]["run_id"] == "run-new"


def test_list_runs_filter_task(reader_with_logs: AuditReader):
    runs = reader_with_logs.list_runs(task="task-a.md")
    assert len(runs) == 1
    assert runs[0]["run_id"] == "run-old"


def test_list_runs_filter_since(reader_with_logs: AuditReader):
    since = datetime.now(timezone.utc) - timedelta(minutes=1)
    runs = reader_with_logs.list_runs(since=since.isoformat())
    assert len(runs) == 2


def test_list_runs_filter_relative_since(reader_with_logs: AuditReader):
    runs = reader_with_logs.list_runs(since="1d")
    assert len(runs) == 2


def test_list_runs_filter_executor_plugin(reader_with_logs: AuditReader):
    logger = AuditLogger()
    logger.log_event(
        RunEvent(
            run_id="run-plugin",
            task="task-c.md",
            executor_plugin="docker",
            result="done",
        )
    )
    runs = reader_with_logs.list_runs(executor_plugin="docker")
    assert len(runs) == 1
    assert runs[0]["run_id"] == "run-plugin"


def test_get_run_exists(reader_with_logs: AuditReader):
    detail = reader_with_logs.get_run("run-new")
    assert detail is not None
    assert detail["run_id"] == "run-new"
    assert len(detail["events"]) == 2


def test_get_run_not_found(reader_with_logs: AuditReader):
    assert reader_with_logs.get_run("missing") is None


def test_get_run_corrupt_line_skipped(tmp_path):
    log_dir = tmp_path / "audit"
    log_dir.mkdir()
    log_path = log_dir / "audit_bad.jsonl"
    log_path.write_text('{"event_type":"run","run_id":"bad","task":"t"}\nnot-json\n', encoding="utf-8")
    reader = AuditReader(log_dir)
    detail = reader.get_run("bad")
    assert detail is not None
    assert len(detail["events"]) == 1
    errors_dir = log_dir / ".audit" / "errors"
    assert list(errors_dir.glob("corrupt_*.jsonl"))


def test_search(reader_with_logs: AuditReader):
    results = reader_with_logs.search(event_type="verify")
    assert len(results) == 1
    assert results[0]["event_type"] == "verify"
