"""SDK builder tests"""

from __future__ import annotations

from pathlib import Path

import pytest

from harness_sdk.builder import build_hat_prompt
from harness_probe.io import load_graph, parse_task_markdown


REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def sample_graph():
    return load_graph(REPO_ROOT / "data" / "graph" / "sample_graph_v2.json")


@pytest.fixture
def sample_task():
    return parse_task_markdown(REPO_ROOT / "data" / "tasks" / "sample_task.md")


def test_build_10_spec_prompt(sample_graph, sample_task):
    from harness_sdk.graph import query_subgraph
    subgraph = query_subgraph(sample_graph, sample_task.entry_node, depth=2)
    compiled = build_hat_prompt("10-spec", sample_graph, sample_task, subgraph, [])
    assert "10-spec" in compiled.semi_static
    assert "SPEC 草案" in compiled.dynamic_suffix
    assert compiled.full_text


def test_build_10_task_prompt(sample_graph, sample_task):
    from harness_sdk.graph import query_subgraph
    subgraph = query_subgraph(sample_graph, sample_task.entry_node, depth=2)
    compiled = build_hat_prompt("10-task", sample_graph, sample_task, subgraph, [])
    assert "10-task" in compiled.semi_static
    assert "task.md 骨架" in compiled.dynamic_suffix


def test_build_20_review_prompt(sample_graph, sample_task):
    from harness_sdk.graph import query_subgraph
    task = sample_task.model_copy(update={"review_target": "task"})
    subgraph = query_subgraph(sample_graph, task.entry_node, depth=2)
    compiled = build_hat_prompt("20-review", sample_graph, task, subgraph, [])
    assert "20-review" in compiled.semi_static
    assert "approved / blocked" in compiled.dynamic_suffix


def test_build_30_prompt(sample_graph, sample_task):
    from harness_sdk.graph import query_subgraph
    subgraph = query_subgraph(sample_graph, sample_task.entry_node, depth=2)
    compiled = build_hat_prompt("30", sample_graph, sample_task, subgraph, [])
    assert "AcceptanceContract" in compiled.semi_static
    assert "failure_path_ref" in compiled.dynamic_suffix


def test_build_40_prompt(sample_graph, sample_task):
    from harness_sdk.graph import query_subgraph
    subgraph = query_subgraph(sample_graph, sample_task.entry_node, depth=2)
    compiled = build_hat_prompt("40", sample_graph, sample_task, subgraph, [])
    assert "AcceptanceContract" in compiled.semi_static


def test_build_50_reinspect_prompt(sample_graph, sample_task):
    from harness_sdk.graph import query_subgraph
    task = sample_task.model_copy(update={"reinspect_mode": "global"})
    subgraph = query_subgraph(sample_graph, task.entry_node, depth=2)
    compiled = build_hat_prompt("50-reinspect", sample_graph, task, subgraph, [])
    assert "50-reinspect global" in compiled.dynamic_suffix
    assert "CLOSE" in compiled.dynamic_suffix


def test_unsupported_hat(sample_graph, sample_task):
    from harness_sdk.graph import query_subgraph
    subgraph = query_subgraph(sample_graph, sample_task.entry_node, depth=2)
    with pytest.raises(ValueError, match="Unsupported hat"):
        build_hat_prompt("99-foo", sample_graph, sample_task, subgraph, [])
