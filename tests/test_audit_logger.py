"""审计日志记录器测试"""

from __future__ import annotations

import json
import warnings

import pytest

from harness_sdk.audit import AuditLogger, get_default_log_dir
from harness_sdk.audit.events import RunEvent


@pytest.fixture
def tmp_logger(tmp_path):
    AuditLogger.reset()
    log_dir = tmp_path / "audit"
    logger = AuditLogger(config={"log_dir": str(log_dir)})
    yield logger
    AuditLogger.reset()


def test_get_default_log_dir():
    assert get_default_log_dir().name == "audit"


def test_log_event_creates_file(tmp_logger: AuditLogger):
    event = RunEvent(
        run_id="run-001",
        task="data/tasks/sample_task.md",
        hat="30,40",
        result="done",
        duration_ms=123,
    )
    tmp_logger.log_event(event)
    log_path = tmp_logger.get_log_dir() / "audit_run-001.jsonl"
    assert log_path.exists()
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["event_type"] == "run"
    assert data["run_id"] == "run-001"
    assert data["result"] == "done"


def test_log_event_appends_to_same_run(tmp_logger: AuditLogger):
    event1 = RunEvent(run_id="run-002", task="t.md", result="done")
    event2 = RunEvent(run_id="run-002", task="t.md", result="done")
    tmp_logger.log_event(event1)
    tmp_logger.log_event(event2)
    log_path = tmp_logger.get_log_dir() / "audit_run-002.jsonl"
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2


def test_log_event_creates_directory(tmp_path):
    AuditLogger.reset()
    log_dir = tmp_path / "nested" / "audit"
    logger = AuditLogger(config={"log_dir": str(log_dir)})
    logger.log_event(RunEvent(run_id="run-003", task="t.md", result="done"))
    assert log_dir.exists()
    AuditLogger.reset()


def test_log_event_retention_by_max_files(tmp_path):
    AuditLogger.reset()
    log_dir = tmp_path / "audit"
    logger = AuditLogger(config={"log_dir": str(log_dir), "retention": {"max_files": 2}})
    for i in range(4):
        logger.log_event(RunEvent(run_id=f"run-{i}", task="t.md", result="done"))
    files = sorted(log_dir.glob("audit_*.jsonl"))
    assert len(files) == 2
    AuditLogger.reset()


def test_log_event_memory_fallback_on_unwritable_dir(tmp_path):
    AuditLogger.reset()
    log_dir = tmp_path / "readonly"
    log_dir.mkdir()
    log_dir.chmod(0o555)
    logger = AuditLogger(config={"log_dir": str(log_dir)})
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        logger.log_event(RunEvent(run_id="run-mem", task="t.md", result="done"))
        assert logger.is_memory_fallback()
        assert any("in-memory" in str(warning.message) for warning in w)
    assert logger.get_memory_logs()
    log_dir.chmod(0o755)
    AuditLogger.reset()


def test_log_event_env_override(tmp_path, monkeypatch):
    AuditLogger.reset()
    env_dir = tmp_path / "env_audit"
    monkeypatch.setenv("HARNESS_AUDIT_LOG_DIR", str(env_dir))
    logger = AuditLogger(config={"log_dir": str(tmp_path / "ignored")})
    assert logger.get_log_dir() == env_dir
    AuditLogger.reset()
