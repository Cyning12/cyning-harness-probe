"""MCP tool tests"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness_mcp.server import create_server


REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_TASK = str(REPO_ROOT / "data" / "tasks" / "sample_task.md")


@pytest.fixture
def mcp():
    return create_server()


@pytest.mark.asyncio
async def test_mcp_probe_verify(mcp):
    result = await mcp.call_tool("probe_verify", {"task_path": SAMPLE_TASK})
    text = result[0][0].text
    data = json.loads(text)
    assert data["ok"] is True
    assert data["errors"] == []


@pytest.mark.asyncio
async def test_mcp_probe_compile(mcp):
    result = await mcp.call_tool(
        "probe_compile",
        {"task_path": SAMPLE_TASK, "entry_node": "RAG", "hat": "30"},
    )
    text = result[0][0].text
    data = json.loads(text)
    assert data["ok"] is True
    assert data["hat"] == "30"
    assert "static_ratio" in data


@pytest.mark.asyncio
async def test_mcp_probe_run(mcp, tmp_path):
    result = await mcp.call_tool(
        "probe_run",
        {
            "task_path": SAMPLE_TASK,
            "entry_node": "RAG",
            "from_hat": "30",
            "to_hat": "40",
        },
    )
    text = result[0][0].text
    data = json.loads(text)
    assert data["ok"] is True
    assert data["status"] == "done"
    assert len(data["nodes"]) == 2


@pytest.mark.asyncio
async def test_mcp_probe_audit(mcp, tmp_path):
    # First create a task_run file
    from harness_probe.io import load_graph, load_wiki_stub, parse_task_markdown, persist_run_graph
    from harness_sdk import TaskRunner

    graph = load_graph(REPO_ROOT / "data" / "graph" / "sample_graph_v2.json")
    task = parse_task_markdown(SAMPLE_TASK)
    wiki = load_wiki_stub(REPO_ROOT / "data" / "wiki" / "syntheses_stub.json")
    runner = TaskRunner(task, graph, wiki)
    run_graph = runner.run_sequence(from_hat="30", to_hat="40")
    run_path = tmp_path / "task_run_test.json"
    persist_run_graph(run_path, run_graph)

    result = await mcp.call_tool(
        "probe_audit",
        {"run_output_path": str(run_path), "mode": "independent"},
    )
    text = result[0][0].text
    data = json.loads(text)
    assert data["ok"] is True
    assert data["verdict"] == "pass"
