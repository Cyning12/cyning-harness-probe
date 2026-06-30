"""SDK executor tests"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness_probe.io import load_graph, load_wiki_stub, parse_task_markdown
from harness_sdk import SubprocessExecutor, TaskRunner
from harness_sdk.models import AcceptanceContract, ExecutionResult, HarnessTask

REPO_ROOT = Path(__file__).resolve().parent.parent


def _sample_task_and_deps():
    graph = load_graph(REPO_ROOT / "data" / "graph" / "sample_graph_v2.json")
    task = parse_task_markdown(REPO_ROOT / "data" / "tasks" / "sample_task.md")
    wiki = load_wiki_stub(REPO_ROOT / "data" / "wiki" / "syntheses_stub.json")
    return graph, task, wiki


def _task_with_contracts(contracts: list[AcceptanceContract]) -> HarnessTask:
    """基于 sample task 构造仅含指定 contracts 的 task。"""
    _, task, _ = _sample_task_and_deps()
    return task.model_copy(update={"contracts": contracts})


@pytest.mark.asyncio
async def test_subprocess_executor_echo_ok():
    executor = SubprocessExecutor()
    result = await executor.run("echo ok")
    assert isinstance(result, ExecutionResult)
    assert result.returncode == 0
    assert result.stdout.strip() == "ok"
    assert result.stderr == ""
    assert result.elapsed_ms >= 0
    assert not result.truncated
    assert not result.timed_out


@pytest.mark.asyncio
async def test_subprocess_executor_exit_1():
    executor = SubprocessExecutor()
    result = await executor.run("exit 1")
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == ""


@pytest.mark.asyncio
async def test_subprocess_executor_timeout():
    executor = SubprocessExecutor(timeout=0.1)
    result = await executor.run("sleep 2")
    assert result.returncode == -1
    assert result.timed_out
    assert "timeout" in result.stderr


@pytest.mark.asyncio
async def test_subprocess_executor_stdout_truncation():
    executor = SubprocessExecutor(max_stdout=10)
    result = await executor.run("python -c \"print('A' * 100)\"")
    assert result.truncated
    assert "[truncated]" in result.stdout
    assert len(result.stdout) == 10 + len("\n[truncated]")


def test_runner_default_mock_behavior_unchanged():
    """未传 executor 时保持 v0.5 dry-run 行为。"""
    graph, task, wiki = _sample_task_and_deps()
    runner = TaskRunner(task, graph, wiki)
    run_graph = runner.run_sequence()
    assert run_graph.status == "done"
    for node in run_graph.nodes:
        assert node.status.value == "done"
        evidence = json.loads(node.evidence)
        for row in evidence:
            assert row["pass_fail"] == "pass"
            assert "dry-run" in row["evidence"]


def test_runner_subprocess_executor_real_verify():
    """TaskRunner(executor=SubprocessExecutor()) 真实执行 contract.verify。"""
    graph, task, wiki = _sample_task_and_deps()
    task = _task_with_contracts(
        [
            AcceptanceContract(
                ref="F1",
                trigger="echo test",
                expected="ok",
                retry="no",
                verify="echo ok",
            ),
            AcceptanceContract(
                ref="F2",
                trigger="fail test",
                expected="non-zero",
                retry="no",
                verify="exit 1",
            ),
        ]
    )
    runner = TaskRunner(task, graph, wiki, executor=SubprocessExecutor())
    run_graph = runner.run_sequence(from_hat="30", to_hat="40")
    assert run_graph.status == "done"
    assert len(run_graph.nodes) == 2

    f1_node = next(n for n in run_graph.nodes if n.hat == "30")
    f1_evidence = json.loads(f1_node.evidence)
    assert len(f1_evidence) == 2
    assert f1_evidence[0]["ref"] == "F1"
    assert f1_evidence[0]["pass_fail"] == "pass"
    assert json.loads(f1_evidence[0]["evidence"])["stdout"].strip() == "ok"

    assert f1_evidence[1]["ref"] == "F2"
    assert f1_evidence[1]["pass_fail"] == "fail"
    assert json.loads(f1_evidence[1]["evidence"])["returncode"] == 1


def test_runner_executor_none_uses_mock_even_with_mock_executor_unset():
    """mock_executor 未设置且 executor 为 None 时仍走 mock。"""
    graph, task, wiki = _sample_task_and_deps()
    runner = TaskRunner(task, graph, wiki, executor=None)
    run_graph = runner.run_sequence(from_hat="30", to_hat="40")
    for node in run_graph.nodes:
        evidence = json.loads(node.evidence)
        for row in evidence:
            assert "dry-run" in row["evidence"]


def test_runner_mock_executor_takes_precedence():
    """mock_executor 仍可用且优先于 executor。"""
    graph, task, wiki = _sample_task_and_deps()

    def mock_executor(task, hat, compiled):
        return {"ref": "FX", "pass_fail": "pass", "evidence": "legacy mock"}

    runner = TaskRunner(
        task,
        graph,
        wiki,
        mock_executor=mock_executor,
        executor=SubprocessExecutor(),
    )
    run_graph = runner.run_sequence(from_hat="30", to_hat="30")
    evidence = json.loads(run_graph.nodes[0].evidence)
    assert evidence[0]["evidence"] == "legacy mock"
