"""SDK runner tests"""

from __future__ import annotations

from pathlib import Path

import pytest

from harness_probe.io import load_graph, load_wiki_stub, parse_task_markdown
from harness_sdk import TaskRunner
from harness_sdk.exceptions import BlockedError
from harness_sdk.models import HumanGate


REPO_ROOT = Path(__file__).resolve().parent.parent


def _sample_task_and_deps():
    graph = load_graph(REPO_ROOT / "data" / "graph" / "sample_graph_v2.json")
    task = parse_task_markdown(REPO_ROOT / "data" / "tasks" / "sample_task.md")
    wiki = load_wiki_stub(REPO_ROOT / "data" / "wiki" / "syntheses_stub.json")
    return graph, task, wiki


def test_runner_dry_run_sequence():
    graph, task, wiki = _sample_task_and_deps()
    runner = TaskRunner(task, graph, wiki)
    run_graph = runner.run_sequence()
    assert run_graph.status == "done"
    assert len(run_graph.nodes) == len(task.planned_hats)
    assert runner.get_last_prompts()


def test_runner_from_to_hat_filter():
    graph, task, wiki = _sample_task_and_deps()
    runner = TaskRunner(task, graph, wiki)
    run_graph = runner.run_sequence(from_hat="30", to_hat="40")
    hats = [n.hat for n in run_graph.nodes]
    assert hats == ["30", "40"]


def test_runner_gate_scan_blocks_pending():
    graph, task, wiki = _sample_task_and_deps()
    task = task.model_copy(
        update={
            "human_gates": [
                HumanGate(gate_id="HG-AUDIT-R1", status="pending", blocks_hats=["30"])
            ]
        }
    )
    runner = TaskRunner(task, graph, wiki)
    with pytest.raises(BlockedError):
        runner.run_sequence()


def test_runner_pre_spawn_verify_no_contracts():
    graph, task, wiki = _sample_task_and_deps()
    task = task.model_copy(update={"contracts": []})
    runner = TaskRunner(task, graph, wiki)
    with pytest.raises(BlockedError, match="failure_paths"):
        runner.run_sequence()


def test_runner_propose_graph_evolution():
    note = TaskRunner.propose_graph_evolution_note("test insight")
    assert "human review required" in note
    assert "forbidden" in note
