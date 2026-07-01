"""CLI 审计子命令集成测试"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness_probe.cli import main
from harness_sdk.audit import AuditLogger


REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_TASK = str(REPO_ROOT / "data" / "tasks" / "sample_task.md")


@pytest.fixture(autouse=True)
def _reset_logger(tmp_path, monkeypatch):
    AuditLogger.reset()
    audit_dir = tmp_path / "audit"
    monkeypatch.setenv("HARNESS_AUDIT_LOG_DIR", str(audit_dir))
    yield
    AuditLogger.reset()


def test_cli_run_logs_run_event():
    code = main([
        "run",
        "--task", SAMPLE_TASK,
        "--from-hat", "30",
        "--to-hat", "40",
        "--quiet",
    ])
    assert code == 0
    logger = AuditLogger()
    log_dir = logger.get_log_dir()
    files = list(log_dir.glob("audit_*.jsonl"))
    assert files


def test_cli_run_no_audit_does_not_log():
    code = main([
        "run",
        "--task", SAMPLE_TASK,
        "--from-hat", "30",
        "--to-hat", "40",
        "--quiet",
        "--no-audit",
    ])
    assert code == 0
    logger = AuditLogger()
    log_dir = logger.get_log_dir()
    files = list(log_dir.glob("audit_*.jsonl"))
    assert not files


def test_cli_verify_logs_verify_event():
    code = main(["verify", "--task", SAMPLE_TASK])
    assert code == 0
    logger = AuditLogger()
    log_dir = logger.get_log_dir()
    files = list(log_dir.glob("audit_*.jsonl"))
    assert files
    lines = files[0].read_text(encoding="utf-8").strip().splitlines()
    data = json.loads(lines[0])
    assert data["event_type"] == "verify"
    assert data["result"] == "pass"


def test_cli_compile_logs_compile_event():
    code = main([
        "compile",
        "--task", SAMPLE_TASK,
        "--hat", "30",
        "--quiet",
    ])
    assert code == 0
    logger = AuditLogger()
    log_dir = logger.get_log_dir()
    files = list(log_dir.glob("audit_*.jsonl"))
    assert files


def test_cli_audit_list_and_show():
    main(["verify", "--task", SAMPLE_TASK])
    logger = AuditLogger()
    log_dir = logger.get_log_dir()
    files = list(log_dir.glob("audit_*.jsonl"))
    run_id = json.loads(files[0].read_text(encoding="utf-8").strip().splitlines()[0])["run_id"]

    code = main(["audit", "list"])
    assert code == 0

    code = main(["audit", "show", "--run-id", run_id])
    assert code == 0


def test_cli_audit_show_missing_returns_one():
    code = main(["audit", "show", "--run-id", "does-not-exist"])
    assert code == 1


def test_cli_audit_report():
    main(["verify", "--task", SAMPLE_TASK])
    code = main(["audit", "report", "--format", "json"])
    assert code == 0


def test_cli_audit_config():
    code = main(["audit", "config"])
    assert code == 0
    data = json.loads(_capture_stdout(["audit", "config"]))
    assert "log_dir" in data


def _capture_stdout(argv: list[str]) -> str:
    import io
    import sys

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        main(argv)
        return sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout
