"""CLI integration tests"""

from __future__ import annotations

from pathlib import Path

import pytest

from harness_probe.cli import main


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_cli_verify_pass():
    code = main(["verify", "--task", str(REPO_ROOT / "data" / "tasks" / "sample_task.md")])
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
