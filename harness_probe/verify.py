"""Harness Probe · 本地可执行验收（P0-2 Verify）

对外提供结构化 VerifyReport 与 verify_task；被 harness_probe.cli 的 verify 子命令调用。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from harness_sdk.task_parser import parse_task_file
from harness_sdk.task_schema import TaskSchema, TestStrategy


class VerifyCheck(BaseModel):
    """单个检查项结果。"""

    name: str
    passed: bool
    message: str
    duration_ms: int


class VerifyReport(BaseModel):
    """verify_task 返回的结构化报告。"""

    task_path: str
    passed: bool
    blockers: list[str]
    checks: list[VerifyCheck]
    summary: str


class _CheckTimer:
    """辅助记录检查耗时（毫秒）。"""

    def __init__(self) -> None:
        self._start = time.perf_counter()

    def elapsed_ms(self) -> int:
        return int((time.perf_counter() - self._start) * 1000)


def _repo_root() -> Path:
    """返回仓库根目录。"""
    return Path(__file__).resolve().parent.parent


def _extract_raw_gate_statuses(task_path: Path) -> dict[str, str]:
    """从 Markdown 任务单中抽取人闸 status 原始字符串。

    Pydantic 会把 'completed' 映射为 'approved'，但 strict 模式需要知道原始值。
    """
    text = task_path.read_text(encoding="utf-8")
    statuses: dict[str, str] = {}
    # 匹配 human_gates 下每个条目的 gate_id / status 行（支持 list 或表格形式）
    for block in re.split(r"\n\s*- gate_id:\s*", text):
        gate_id_match = re.search(r"^(?:(?:---|\.\.\.)\s*\n)?\s*([^\n]+)", block, re.M)
        status_match = re.search(r"^\s*status:\s*(.+)", block, re.M)
        if gate_id_match and status_match:
            statuses[gate_id_match.group(1).strip().strip('"\'`')] = status_match.group(1).strip().strip('"\'`')
    return statuses


def _resolve_task_path(task_path: str | Path) -> Path:
    p = Path(task_path)
    if p.is_absolute():
        return p
    return _repo_root() / p


def _resolve_graph_root(graph_root: str | Path | None) -> Path:
    if graph_root is None:
        return _repo_root() / "docs" / "_tech_graph"
    p = Path(graph_root)
    if p.is_absolute():
        return p
    return _repo_root() / p


def verify_human_gates(
    schema: TaskSchema,
    *,
    strict: bool = False,
    raw_statuses: dict[str, str] | None = None,
) -> VerifyCheck:
    """校验任务单中是否有人闸阻塞 hat 30；strict 模式下 completed 也视为非法。"""
    blockers: list[str] = []
    for gate in schema.blocking_gates("30"):
        blockers.append(f"{gate.gate_id} status={gate.status.value} blocks_hats={gate.blocks_hats}")
    if strict:
        # raw_statuses 允许传入解析前的原始 status 字符串，绕过 normalize 映射
        raw_statuses = raw_statuses or {}
        for gate in schema.metadata.human_gates:
            raw = raw_statuses.get(gate.gate_id, gate.status.value)
            if raw == "completed":
                blockers.append(
                    f"STRICT-COMPLETED-ILLEGAL: gate {gate.gate_id} "
                    "uses deprecated status 'completed', use 'approved'"
                )
    passed = not blockers
    return VerifyCheck(
        name="human_gates",
        passed=passed,
        message=("OK · no human gates block hat 30" if passed else "BLOCKED: " + "; ".join(blockers)),
        duration_ms=0,
    )


def verify_graph_delta(
    task_path: str | Path,
    schema: TaskSchema,
    graph_root: str | Path | None = None,
) -> VerifyCheck:
    """校验任务单声明的 graph_delta 文件是否存在。"""
    timer = _CheckTimer()
    delta = schema.metadata.graph_delta
    if not delta:
        return VerifyCheck(
            name="graph_delta",
            passed=True,
            message="OK · no graph_delta declared",
            duration_ms=timer.elapsed_ms(),
        )

    first_token = delta.strip().split()[0].lower().strip("()`")
    normalized = first_token.split("（")[0].split("(")[0]
    if normalized in {"none", "n/a", ""}:
        return VerifyCheck(
            name="graph_delta",
            passed=True,
            message="OK · graph_delta declared as none/n/a",
            duration_ms=timer.elapsed_ms(),
        )

    root = _resolve_graph_root(graph_root)
    if Path(delta).is_absolute():
        target = Path(delta)
    else:
        target = root / delta
        if not target.exists():
            target = _repo_root() / delta

    if target.exists():
        return VerifyCheck(
            name="graph_delta",
            passed=True,
            message=f"OK · {target}",
            duration_ms=timer.elapsed_ms(),
        )

    rel = _relative_to_root(target)
    return VerifyCheck(
        name="graph_delta",
        passed=False,
        message=f"graph_delta file missing: {rel}",
        duration_ms=timer.elapsed_ms(),
    )


def _relative_to_root(path: Path) -> str:
    root = _repo_root()
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _resolve_external_tool_cmd(module: str, *args: str) -> list[str] | None:
    """解析外部工具命令：优先 PATH 可执行文件，否则尝试 ``python -m <module>``。"""
    binary = shutil.which(module)
    if binary:
        return [binary, *args]
    python_exe = sys.executable
    probe = subprocess.run(
        [python_exe, "-m", module, "--version"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if probe.returncode == 0:
        return [python_exe, "-m", module, *args]
    return None


def _task_slug(task_path: Path) -> str:
    """从任务单文件名提取 slug（去 task_ 前缀与版本后缀）。"""
    name = task_path.stem
    if name.startswith("task_"):
        name = name[len("task_") :]
    parts = name.split("_")
    while parts and (
        parts[-1].startswith("v")
        or parts[-1].replace("v", "").replace(".", "").replace("-", "").isdigit()
    ):
        parts.pop()
    return "_".join(parts)


def _expected_test_files(task_path: Path) -> list[Path]:
    """根据任务单文件名启发式推断期望的测试文件。

    规则：去掉文件名前缀 ``task_``，再去除末尾版本号 ``_v0_x_0_v1`` / ``_v1``，
    取剩余片段映射到 ``tests/test_<片段>.py``。优先在任务单同目录下的 ``tests/`` 查找，
    再回退到仓库根 ``tests/``；若 slug 为空则做子串匹配。
    """
    name = task_path.stem
    if name.startswith("task_"):
        name = name[len("task_") :]
    slug = _task_slug(task_path)
    search_dirs = [task_path.parent / "tests", _repo_root() / "tests"]
    candidates: list[Path] = []
    for test_dir in search_dirs:
        if not test_dir.is_dir():
            continue
        if slug:
            found = sorted(test_dir.glob(f"test_{slug}*.py"))
            if found:
                candidates = found
                break
    # 回退：如果 slug 为空或没匹配，尝试用原始文件名核心词（去 task_/版本）做子串匹配
    if not candidates:
        core = name
        for suffix in ("_v1", "_v0_1_0_v1", "_v0_10_0_v1"):
            if core.endswith(suffix):
                core = core[: -len(suffix)]
        keywords = [core] + core.split("_")
        for test_dir in search_dirs:
            if not test_dir.is_dir():
                continue
            candidates = sorted(
                {p for kw in keywords if kw for p in test_dir.glob("test_*.py") if kw in p.stem}
            )
            if candidates:
                break
    return candidates


def _verify_test_strategy(
    task_path: Path,
    schema: TaskSchema,
) -> VerifyCheck:
    """检查 test_strategy 合法性与对应测试文件是否存在。"""
    timer = _CheckTimer()
    strategy = schema.metadata.test_strategy
    if strategy is None:
        return VerifyCheck(
            name="test_strategy",
            passed=True,
            message="OK · no test_strategy declared",
            duration_ms=timer.elapsed_ms(),
        )

    if strategy == TestStrategy.required:
        expected = _expected_test_files(task_path)
        if not expected:
            rel = _relative_to_root(task_path)
            return VerifyCheck(
                name="test_strategy",
                passed=False,
                message=f"test_strategy=required but no matching test file found for {rel}",
                duration_ms=timer.elapsed_ms(),
            )
        return VerifyCheck(
            name="test_strategy",
            passed=True,
            message=f"OK · required tests found: {', '.join(_relative_to_root(p) for p in expected)}",
            duration_ms=timer.elapsed_ms(),
        )

    if strategy == TestStrategy.recommended:
        return VerifyCheck(
            name="test_strategy",
            passed=True,
            message="OK · test_strategy recommended (optional)",
            duration_ms=timer.elapsed_ms(),
        )

    return VerifyCheck(
        name="test_strategy",
        passed=True,
        message="OK · test_strategy not_applicable",
        duration_ms=timer.elapsed_ms(),
    )


def _run_subprocess_check(
    name: str,
    cmd: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: float = 180.0,
    _runner: Any | None = None,
) -> VerifyCheck:
    """运行外部命令并返回 VerifyCheck。

    ``_runner`` 允许测试注入 mock 的 subprocess.run 替代函数。
    """
    timer = _CheckTimer()
    if env is None:
        env = dict(os.environ)
    program = cmd[0]
    if shutil.which(program) is None:
        return VerifyCheck(
            name=name,
            passed=False,
            message=f"{program}: command not found",
            duration_ms=timer.elapsed_ms(),
        )

    run = _runner or subprocess.run
    try:
        result = run(
            cmd,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return VerifyCheck(
            name=name,
            passed=False,
            message=f"{' '.join(cmd)} timed out after {timeout}s",
            duration_ms=timer.elapsed_ms(),
        )
    except OSError as exc:
        return VerifyCheck(
            name=name,
            passed=False,
            message=f"{' '.join(cmd)} failed: {exc}",
            duration_ms=timer.elapsed_ms(),
        )

    if result.returncode == 0:
        return VerifyCheck(
            name=name,
            passed=True,
            message=f"OK · {' '.join(cmd)}",
            duration_ms=timer.elapsed_ms(),
        )

    output = (result.stdout + "\n" + result.stderr).strip()
    if not output:
        output = "(no output)"
    return VerifyCheck(
        name=name,
        passed=False,
        message=f"{' '.join(cmd)} failed:\n{output}",
        duration_ms=timer.elapsed_ms(),
    )


def _build_env(env: str | None) -> dict[str, str]:
    """根据环境名，通过 ConfigManager 读取一次配置并返回环境变量副本。"""
    base = dict(os.environ)
    if env:
        base["HARNESS_ENV"] = env
    return base


def verify_task(
    task_path: str | Path,
    graph_root: str | Path | None = None,
    *,
    strict: bool = False,
    env: str | None = None,
    run_external_checks: bool = True,
    _subprocess_runner: Any = None,
) -> VerifyReport:
    """对给定任务单执行完整本地验证流程并返回 VerifyReport。

    参数 ``run_external_checks`` 用于测试场景：置为 False 时只做人闸、graph_delta、
    test_strategy 校验，不真正启动 pytest/ruff/mypy，避免测试递归。
    ``_subprocess_runner`` 允许注入 subprocess 替代函数，便于测试 mock。
    """
    task_path_resolved = _resolve_task_path(task_path)
    repo_root = _repo_root()

    if not task_path_resolved.is_file():
        return VerifyReport(
            task_path=str(task_path),
            passed=False,
            blockers=[f"task file not found: {_relative_to_root(task_path_resolved)}"],
            checks=[],
            summary=f"task file not found: {_relative_to_root(task_path_resolved)}",
        )

    try:
        schema, _warnings = parse_task_file(task_path_resolved)
    except Exception as exc:  # noqa: BLE001 — 解析失败统一返回失败报告
        return VerifyReport(
            task_path=str(task_path),
            passed=False,
            blockers=[f"parse_error: {exc}"],
            checks=[],
            summary=f"parse_error: {exc}",
        )

    raw_statuses = _extract_raw_gate_statuses(task_path_resolved)
    run_env = _build_env(env)
    # 外部检查在任务单所在目录运行，允许 CLI 测试使用临时测试文件
    check_cwd = task_path_resolved.parent

    checks: list[VerifyCheck] = []
    gate_check = verify_human_gates(schema, strict=strict, raw_statuses=raw_statuses)
    checks.append(gate_check)
    graph_check = verify_graph_delta(task_path_resolved, schema, graph_root)
    checks.append(graph_check)
    test_strategy_check = _verify_test_strategy(task_path_resolved, schema)
    checks.append(test_strategy_check)

    # 外部工具检查可由调用方关闭或注入，避免测试时递归启动 pytest。
    # 外部检查只跑该任务对应的测试文件，避免全仓 pytest 触发递归/雪崩。
    if run_external_checks:
        runner = _subprocess_runner or subprocess.run
        python_exe = sys.executable

        test_files = _expected_test_files(task_path_resolved)
        if test_files:
            pytest_cmd = [python_exe, "-m", "pytest"] + [str(f) for f in test_files] + ["-q", "--maxfail=3"]
        else:
            pytest_cmd = [python_exe, "-m", "pytest", "-q", "--maxfail=3", "--co", "-q"]
        pytest_check = _run_subprocess_check(
            "pytest",
            pytest_cmd,
            cwd=check_cwd,
            env=run_env,
            timeout=120.0,
            _runner=runner,
        )
        checks.append(pytest_check)
        ruff_cmd = _resolve_external_tool_cmd("ruff", "check", ".")
        if ruff_cmd:
            ruff_check = _run_subprocess_check(
                "ruff",
                ruff_cmd,
                cwd=repo_root,
                env=run_env,
                timeout=60.0,
                _runner=runner,
            )
            checks.append(ruff_check)
        mypy_cmd = _resolve_external_tool_cmd("mypy", "harness_sdk")
        if mypy_cmd:
            mypy_check = _run_subprocess_check(
                "mypy",
                mypy_cmd,
                cwd=repo_root,
                env=run_env,
                timeout=60.0,
                _runner=runner,
            )
            checks.append(mypy_check)

    blockers = [c.message for c in checks if not c.passed]
    passed = not blockers
    total = len(checks)
    ok = sum(1 for c in checks if c.passed)
    summary = f"{task_path_resolved} · {ok}/{total} checks passed"

    return VerifyReport(
        task_path=str(task_path),
        passed=passed,
        blockers=blockers,
        checks=checks,
        summary=summary,
    )


def report_to_json(report: VerifyReport) -> str:
    """将单报告序列化为 JSON 字符串。"""
    return json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False)


def report_to_markdown(report: VerifyReport) -> str:
    """将单报告渲染为 Markdown 表格。"""
    status = "PASSED" if report.passed else "FAILED"
    lines = [
        f"# Verify Report · {status}",
        "",
        f"**task_path**: `{report.task_path}`",
        f"**summary**: {report.summary}",
        "",
        "| check | status | message |",
        "|-------|--------|---------|",
    ]
    for c in report.checks:
        msg = c.message.replace("\n", " ")
        lines.append(f"| {c.name} | {'PASS' if c.passed else 'FAIL'} | {msg} |")
    if report.blockers:
        lines.extend(["", "**blockers**:", ""])
        for b in report.blockers:
            lines.append(f"- {b.replace(chr(10), ' ')}")
    return "\n".join(lines)


def aggregate_reports_to_json(reports: list[VerifyReport]) -> str:
    """将批量报告序列化为 JSON 字符串。"""
    return json.dumps([r.model_dump(mode="json") for r in reports], indent=2, ensure_ascii=False)


def aggregate_reports_to_markdown(reports: list[VerifyReport]) -> str:
    """将批量报告渲染为 Markdown 摘要。"""
    total = len(reports)
    passed = sum(1 for r in reports if r.passed)
    lines = [
        f"# Verify Batch Report · {passed}/{total} tasks passed",
        "",
        "| task | status | summary |",
        "|------|--------|---------|",
    ]
    for r in reports:
        status = "PASSED" if r.passed else "FAILED"
        summary = r.summary.replace("\n", " ")
        lines.append(f"| `{r.task_path}` | {status} | {summary} |")
    return "\n".join(lines)
