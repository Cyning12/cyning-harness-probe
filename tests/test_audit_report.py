"""审计报告测试"""

from __future__ import annotations

import json

import pytest

from harness_sdk.audit import AuditLogger
from harness_sdk.audit.events import RunEvent
from harness_sdk.audit.reader import AuditReader
from harness_sdk.audit.report import AuditReport


@pytest.fixture
def report_with_data(tmp_path):
    AuditLogger.reset()
    log_dir = tmp_path / "audit"
    logger = AuditLogger(config={"log_dir": str(log_dir)})
    logger.log_event(RunEvent(run_id="r1", task="t1.md", result="done", duration_ms=100))
    logger.log_event(RunEvent(run_id="r2", task="t2.md", result="blocked", duration_ms=200))
    reader = AuditReader(log_dir)
    yield AuditReport(reader=reader)
    AuditLogger.reset()


def test_to_json_summary(report_with_data: AuditReport):
    text = report_with_data.to_json()
    data = json.loads(text)
    assert data["summary"]["total_runs"] == 2
    assert data["summary"]["done"] == 1
    assert data["summary"]["blocked"] == 1
    assert data["summary"]["total_duration_ms"] == 300
    assert len(data["runs"]) == 2


def test_to_markdown_contains_summary(report_with_data: AuditReport):
    text = report_with_data.to_markdown()
    assert "总运行数 | 2" in text
    assert "成功 | 1" in text
    assert "阻塞 | 1" in text
    assert "r1" in text
    assert "r2" in text


def test_report_filter_task(report_with_data: AuditReport):
    report_with_data.task = "t1.md"
    data = json.loads(report_with_data.to_json())
    assert data["summary"]["total_runs"] == 1
    assert data["runs"][0]["task"] == "t1.md"


def test_report_write(tmp_path):
    AuditLogger.reset()
    log_dir = tmp_path / "audit"
    logger = AuditLogger(config={"log_dir": str(log_dir)})
    logger.log_event(RunEvent(run_id="w1", task="t.md", result="done"))
    report = AuditReport(reader=AuditReader(log_dir))
    out = tmp_path / "report.json"
    report.write(out, fmt="json")
    assert out.exists()
    assert json.loads(out.read_text(encoding="utf-8"))["summary"]["total_runs"] == 1
    AuditLogger.reset()
