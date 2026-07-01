"""CLI integration tests"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness_probe.cli import main


REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_TASK = str(REPO_ROOT / "data" / "tasks" / "sample_task.md")


def test_cli_verify_pass():
    code = main(["verify", "--task", SAMPLE_TASK])
    assert code == 0


def test_cli_compile_quiet():
    code = main(["compile", "--hat", "30", "--quiet"])
    assert code == 0


def test_cli_run_range():
    code = main([
        "run",
        "--from-hat", "30",
        "--to-hat", "40",
        "--quiet",
    ])
    assert code == 0


def test_cli_run_executor_mock_default():
    code = main([
        "run",
        "--task", SAMPLE_TASK,
        "--from-hat", "30",
        "--to-hat", "40",
        "--quiet",
    ])
    assert code == 0
    outputs = sorted((REPO_ROOT / "outputs").glob("task_run_*.json"))
    assert outputs
    run_graph = json.loads(outputs[-1].read_text(encoding="utf-8"))
    assert run_graph["status"] == "done"
    for node in run_graph["nodes"]:
        evidence = json.loads(node["evidence"])
        for row in evidence:
            assert "dry-run" in row["evidence"]


def test_cli_run_executor_real():
    code = main([
        "run",
        "--task", SAMPLE_TASK,
        "--executor", "real",
        "--from-hat", "30",
        "--to-hat", "40",
        "--quiet",
    ])
    assert code == 0
    outputs = sorted((REPO_ROOT / "outputs").glob("task_run_*.json"))
    assert outputs
    # 测试运行可能产生其他 task_run 文件，按 mtime 取最新
    run_graph = json.loads(max(outputs, key=lambda p: p.stat().st_mtime).read_text(encoding="utf-8"))
    # sample_task verify 命令为示例且会失败，因此 graph 被标记为 blocked
    assert run_graph["status"] == "blocked"
    for node in run_graph["nodes"]:
        evidence = json.loads(node["evidence"])
        for row in evidence:
            assert "dry-run" not in row["evidence"]
            ev = json.loads(row["evidence"])
            assert "returncode" in ev
            assert "stdout" in ev
            assert "stderr" in ev


def test_cli_run_executor_plugin_dry_run():
    code = main([
        "run",
        "--task", SAMPLE_TASK,
        "--executor-plugin", "dry-run",
        "--from-hat", "30",
        "--to-hat", "40",
        "--quiet",
    ])
    assert code == 0
    outputs = sorted((REPO_ROOT / "outputs").glob("task_run_*.json"))
    assert outputs
    run_graph = json.loads(outputs[-1].read_text(encoding="utf-8"))
    assert run_graph["status"] == "done"
    for node in run_graph["nodes"]:
        evidence = json.loads(node["evidence"])
        for row in evidence:
            assert "dry-run" in row["evidence"]


def test_cli_run_executor_plugin_subprocess():
    code = main([
        "run",
        "--task", SAMPLE_TASK,
        "--executor-plugin", "subprocess",
        "--from-hat", "30",
        "--to-hat", "40",
        "--quiet",
    ])
    assert code == 0
    outputs = sorted((REPO_ROOT / "outputs").glob("task_run_*.json"))
    assert outputs
    run_graph = json.loads(max(outputs, key=lambda p: p.stat().st_mtime).read_text(encoding="utf-8"))
    assert run_graph["status"] == "blocked"


def test_cli_run_executor_plugin_preview():
    code = main([
        "run",
        "--task", SAMPLE_TASK,
        "--executor-plugin", "preview",
        "--from-hat", "30",
        "--to-hat", "40",
        "--quiet",
    ])
    assert code == 0
    outputs = sorted((REPO_ROOT / "outputs").glob("task_run_*.json"))
    assert outputs
    run_graph = json.loads(outputs[-1].read_text(encoding="utf-8"))
    assert run_graph["status"] == "done"


def test_cli_run_executor_real_max_retries_blocks():
    code = main([
        "run",
        "--task", SAMPLE_TASK,
        "--executor", "real",
        "--max-retries", "2",
        "--from-hat", "30",
        "--to-hat", "30",
        "--quiet",
    ])
    assert code == 0
    outputs = sorted((REPO_ROOT / "outputs").glob("task_run_*.json"))
    assert outputs
    run_graph = json.loads(max(outputs, key=lambda p: p.stat().st_mtime).read_text(encoding="utf-8"))
    assert run_graph["status"] == "blocked"
    node = run_graph["nodes"][0]
    assert node["status"] == "blocked"
    evidence = json.loads(node["evidence"])
    assert evidence[0]["pass_fail"] == "fail"
    ev = json.loads(evidence[0]["evidence"])
    assert ev["retries"] == 2


def test_cli_graph_query():
    code = main([
        "graph-query",
        "--node", "RAG",
        "--depth", "2",
    ])
    assert code == 0


def test_cli_verify_file_not_found():
    code = main(["verify", "--task", "does_not_exist.md"])
    assert code == 2


def test_cli_mcp_help():
    with pytest.raises(SystemExit) as exc_info:
        main(["mcp", "--help"])
    assert exc_info.value.code == 0


def test_cli_run_cwd_not_found(tmp_path):
    code = main([
        "run",
        "--executor", "real",
        "--cwd", str(tmp_path / "nonexistent"),
        "--from-hat", "30",
        "--to-hat", "30",
    ])
    assert code == 2
