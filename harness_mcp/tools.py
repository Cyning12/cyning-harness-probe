"""MCP Tools · harness-probe"""

from __future__ import annotations

import json
import warnings
from dataclasses import asdict
from pathlib import Path

from harness_mcp.config import get_default_graph_path, get_default_wiki_path, load_mcp_config
from harness_probe.io import (
    load_graph,
    load_wiki_stub,
    parse_task_markdown,
    persist_prompt,
    persist_run_graph,
    validate_task_markdown,
)
from harness_sdk import TaskRunner
from harness_sdk.models import TaskRunGraph


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _resolve_config(config_path: str | None) -> dict:
    if config_path:
        return load_mcp_config(config_path)
    default = _repo_root() / "config" / "probe_config.yaml"
    return load_mcp_config(default)


def _resolve_paths(
    config: dict,
    graph_path: str | None,
    wiki_path: str | None,
) -> tuple[Path, Path]:
    gpath = Path(graph_path) if graph_path else get_default_graph_path(config)
    wpath = Path(wiki_path) if wiki_path else get_default_wiki_path(config)
    if not gpath.is_absolute():
        gpath = _repo_root() / gpath
    if not wpath.is_absolute():
        wpath = _repo_root() / wpath
    return gpath, wpath


async def probe_compile(
    task_path: str,
    entry_node: str,
    hat: str,
    graph_path: str | None = None,
    wiki_path: str | None = None,
    config_path: str | None = None,
) -> str:
    """编译指定帽子的 Subagent Prompt，返回三段式内容。"""
    config = _resolve_config(config_path)
    gpath, wpath = _resolve_paths(config, graph_path, wiki_path)

    graph = load_graph(gpath)
    task = parse_task_markdown(task_path)
    task = task.model_copy(update={"entry_node": entry_node, "planned_hats": [hat]})

    wiki_entries = load_wiki_stub(wpath)
    runner = TaskRunner(task, graph, wiki_entries)
    run_graph = runner.run_sequence()

    compiled = runner.get_last_prompts().get(hat)
    if compiled is None:
        return json.dumps({"ok": False, "error": f"hat {hat} not generated"}, ensure_ascii=False)

    output_dir = _repo_root() / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = output_dir / f"prompt_{run_graph.session_id}_hat{hat}.md"
    persist_prompt(prompt_path, compiled)
    persist_run_graph(output_dir / f"task_run_{run_graph.session_id}.json", run_graph)

    return json.dumps(
        {
            "ok": True,
            "session_id": run_graph.session_id,
            "freeze_id": graph.freeze_id,
            "hat": hat,
            "static_prefix": compiled.static_prefix,
            "semi_static": compiled.semi_static,
            "dynamic_suffix": compiled.dynamic_suffix,
            "static_char_count": compiled.static_char_count,
            "dynamic_char_count": compiled.dynamic_char_count,
            "static_ratio": round(
                compiled.static_char_count
                / (compiled.static_char_count + compiled.dynamic_char_count),
                2,
            )
            if (compiled.static_char_count + compiled.dynamic_char_count)
            else 0,
            "prompt_path": str(prompt_path),
        },
        ensure_ascii=False,
    )


async def probe_run(
    task_path: str,
    entry_node: str,
    from_hat: str,
    to_hat: str,
    graph_path: str | None = None,
    wiki_path: str | None = None,
    mock: bool = True,
    executor: str = "mock",
    max_retries: int = 0,
    cwd: str | None = None,
    dry_run: bool = False,
    safety_mode: str = "whitelist",
    execution_log_dir: str | None = None,
    config_path: str | None = None,
    safety_config: str | None = None,
    preview: bool = False,
    preview_format: str = "json",
) -> str:
    """串行模拟执行多顶帽子，生成 L1.5 task_run 轨迹。"""
    config = _resolve_config(config_path)
    gpath, wpath = _resolve_paths(config, graph_path, wiki_path)

    graph = load_graph(gpath)
    task = parse_task_markdown(task_path)
    task = task.model_copy(update={"entry_node": entry_node})

    wiki_entries = load_wiki_stub(wpath)

    if preview:
        return _probe_run_preview(
            task,
            executor=executor,
            safety_mode=safety_mode,
            execution_log_dir=execution_log_dir,
            config=config,
            safety_config=safety_config,
            preview_format=preview_format,
        )

    real_executor = None
    use_real = executor == "real" or not mock
    if use_real:
        from harness_sdk.executor import SubprocessExecutor

        safety_cfg = config.get("executor", {}).get("safety", {})
        resolved_safety_mode = safety_mode or safety_cfg.get("mode", "whitelist")
        resolved_log_dir = execution_log_dir or safety_cfg.get("execution_log_dir")
        if resolved_log_dir:
            rlp = Path(resolved_log_dir)
            if not rlp.is_absolute():
                rlp = _repo_root() / rlp
            resolved_log_dir = str(rlp)
        from harness_sdk.safety import load_safety_config

        safety_cfg_obj = None
        if safety_config:
            safety_cfg_obj = load_safety_config(safety_config)
        elif safety_cfg.get("config"):
            safety_cfg_obj = load_safety_config(safety_cfg["config"])
        real_executor = SubprocessExecutor(
            safety_mode=resolved_safety_mode,
            dry_run=dry_run,
            execution_log_dir=resolved_log_dir,
            safety_config=safety_cfg_obj,
        )

    if cwd:
        cwd_path = Path(cwd)
        if not cwd_path.is_dir():
            return json.dumps(
                {"ok": False, "error": f"cwd not found or not a directory: {cwd}"},
                ensure_ascii=False,
            )
        cwd = str(cwd_path.resolve())

    runner = TaskRunner(task, graph, wiki_entries, executor=real_executor, cwd=cwd)
    run_graph = runner.run_sequence(from_hat=from_hat, to_hat=to_hat, max_retries=max_retries)

    output_dir = _repo_root() / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    _persist_prompts(runner, run_graph, output_dir)
    run_path = output_dir / f"task_run_{run_graph.session_id}.json"
    persist_run_graph(run_path, run_graph)

    return json.dumps(
        {
            "ok": True,
            "session_id": run_graph.session_id,
            "status": run_graph.status,
            "run_output_path": str(run_path),
            "nodes": [
                {
                    "hat": n.hat,
                    "status": n.status.value,
                    "contract_refs": n.contract_refs,
                    "evidence": n.evidence,
                }
                for n in run_graph.nodes
            ],
        },
        ensure_ascii=False,
    )


def _persist_prompts(runner: TaskRunner, run_graph, output_dir: Path) -> None:
    for hat, compiled in runner.get_last_prompts().items():
        prompt_path = output_dir / f"prompt_{run_graph.session_id}_hat{hat}.md"
        persist_prompt(prompt_path, compiled)


def _probe_run_preview(
    task,
    *,
    executor: str,
    safety_mode: str,
    execution_log_dir: str | None,
    config: dict,
    safety_config: str | None,
    preview_format: str,
) -> str:
    """probe_run 的 preview 模式：不执行命令，返回结构化影响报告。"""
    from harness_sdk.executor import SubprocessExecutor
    from harness_sdk.safety import load_safety_config

    if executor == "real":
        warnings.warn(
            "preview=True takes precedence over executor='real'; no command will be executed",
            stacklevel=2,
        )

    safety_cfg = config.get("executor", {}).get("safety", {})
    resolved_safety_mode = safety_mode or safety_cfg.get("mode", "whitelist")
    resolved_log_dir = execution_log_dir or safety_cfg.get("execution_log_dir")
    if resolved_log_dir:
        rlp = Path(resolved_log_dir)
        if not rlp.is_absolute():
            rlp = _repo_root() / rlp
        resolved_log_dir = str(rlp)

    safety_cfg_obj = None
    if safety_config:
        safety_cfg_obj = load_safety_config(safety_config)
    elif safety_cfg.get("config"):
        safety_cfg_obj = load_safety_config(safety_cfg["config"])

    preview_executor = SubprocessExecutor(
        safety_mode=resolved_safety_mode,
        dry_run=True,
        execution_log_dir=resolved_log_dir,
        safety_config=safety_cfg_obj,
    )

    reports = []
    for contract in task.contracts:
        report = preview_executor.preview(contract.verify)
        data = asdict(report)
        data["ref"] = contract.ref
        reports.append(data)

    if preview_format == "markdown":
        lines = [
            "# Harness Probe · 沙箱预览报告",
            "",
            "| Ref | Command | Parsed | Whitelist | Blacklist | Recommended | Risk |",
            "|-----|---------|--------|-----------|-----------|-------------|------|",
        ]
        for report in reports:
            row = [
                report.get("ref", "-"),
                f"`{report['cmd']}`",
                " ".join(f"`{t}`" for t in report["parsed_tokens"]),
                ", ".join(report["matched_whitelist"]) or "-",
                ", ".join(report["matched_blacklist"]) or "-",
                report["recommended_mode"],
                report["risk_level"],
            ]
            lines.append("| " + " | ".join(row) + " |")
        return json.dumps({"ok": True, "preview": "\n".join(lines)}, ensure_ascii=False)

    return json.dumps({"ok": True, "preview": reports}, ensure_ascii=False)


async def probe_audit(
    run_output_path: str,
    mode: str = "independent",
) -> str:
    """读取 task_run JSON，生成验收 verdict。"""
    path = Path(run_output_path)
    if not path.exists():
        return json.dumps(
            {"ok": False, "error": f"run output not found: {run_output_path}"},
            ensure_ascii=False,
        )

    run_graph = TaskRunGraph.model_validate_json(path.read_text(encoding="utf-8"))
    blocked_nodes = [n for n in run_graph.nodes if n.status.value == "blocked"]
    all_pass = not blocked_nodes and all(n.status.value == "done" for n in run_graph.nodes)

    contract_table = []
    for node in run_graph.nodes:
        evidence = {}
        if node.evidence:
            try:
                evidence = json.loads(node.evidence)
            except json.JSONDecodeError:
                evidence = {"raw": node.evidence}
        if isinstance(evidence, list):
            evidence_map = {row.get("ref", ""): row for row in evidence}
        else:
            evidence_map = evidence
        for ref in node.contract_refs:
            ev = evidence_map.get(ref, {})
            pass_fail = "pass" if node.status.value == "done" else "fail"
            contract_table.append(
                {
                    "ref": ref,
                    "pass_fail": pass_fail,
                    "evidence": ev.get("evidence", "") if isinstance(ev, dict) else str(ev),
                }
            )

    if all_pass:
        return json.dumps(
            {
                "ok": True,
                "verdict": "pass",
                "summary": f"{len(run_graph.nodes)} 个帽子全部通过",
                "contract_table": contract_table,
                "recommendation": "CLOSE · 可合并",
            },
            ensure_ascii=False,
        )

    if blocked_nodes:
        summary = f"{len(blocked_nodes)} 个帽子 blocked：" + ", ".join(n.hat for n in blocked_nodes)
    else:
        summary = "部分帽子未通过"

    return json.dumps(
        {
            "ok": True,
            "verdict": "fail",
            "summary": summary,
            "contract_table": contract_table,
            "recommendation": "打回至 30 · 补跑 verify_cmd",
            "next_hat": "30",
        },
        ensure_ascii=False,
    )


async def probe_verify(
    task_path: str,
) -> str:
    """PRE_SPAWN_VERIFY：校验 task 人闸与 Harness 规则。"""
    path = Path(task_path)
    if not path.exists():
        return json.dumps(
            {"ok": False, "errors": [f"file not found: {task_path}"], "blocked_hats": []},
            ensure_ascii=False,
        )

    errors = validate_task_markdown(path)
    task = parse_task_markdown(path)

    blocked_hats: list[str] = []
    if task.blocks_hat("30") and not task.is_gate_approved("HG-AUDIT-R1"):
        errors.append("HG-AUDIT-R1 pending but blocks 30")
        blocked_hats.append("30")

    return json.dumps(
        {"ok": not errors, "errors": errors, "blocked_hats": blocked_hats},
        ensure_ascii=False,
    )
