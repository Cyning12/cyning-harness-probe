"""Harness Probe CLI"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import uuid
import warnings
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from harness_probe.io import (
    load_graph,
    load_wiki_stub,
    parse_task_markdown,
    persist_prompt,
    persist_run_graph,
    validate_task_markdown,
)
from harness_sdk import ConfigError, ConfigManager, TaskRunner
from harness_sdk.task_parser import parse_task_file
from harness_sdk.audit import AuditLogger, AuditReader, AuditReport
from harness_sdk.audit.events import CompileEvent, RunEvent, VerifyEvent
from harness_sdk.executor import (
    DryRunExecutor,
    PreviewExecutor,
    SubprocessExecutor,
    VerifyExecutor,
    load_executor_plugin,
)
from harness_sdk.graph import query_subgraph
from harness_sdk.capability import CapabilitySet, evaluate_command_risk
from harness_sdk.safety import SafetyConfig, load_safety_config


def _audit_logger() -> AuditLogger:
    return AuditLogger()


def _log_run_event(
    run_id: str,
    task_path: str,
    hats: list[str],
    executor_plugin: str | None,
    result_status: str,
    duration_ms: int,
) -> None:
    logger = _audit_logger()
    logger.log_event(
        RunEvent(
            run_id=run_id,
            task=str(task_path),
            hat=",".join(hats) if hats else None,
            executor_plugin=executor_plugin,
            commands=[],
            result=result_status,
            duration_ms=duration_ms,
        )
    )


def _log_verify_event(
    run_id: str,
    task_path: str,
    verifier: str,
    result: str,
) -> None:
    logger = _audit_logger()
    logger.log_event(
        VerifyEvent(
            run_id=run_id,
            task=str(task_path),
            verifier=verifier,
            result=result,
        )
    )


def _log_compile_event(
    run_id: str,
    task_path: str,
    output_summary: str,
) -> None:
    logger = _audit_logger()
    logger.log_event(
        CompileEvent(
            run_id=run_id,
            task=str(task_path),
            output=output_summary,
        )
    )


def _audit_enabled(args: argparse.Namespace) -> bool:
    return not getattr(args, "no_audit", False)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_config() -> dict:
    cfg_path = _repo_root() / "config" / "probe_config.yaml"
    if not cfg_path.exists():
        return {}
    return yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}


def _resolve_env(args: argparse.Namespace) -> str:
    """解析 CLI --env / -e 与环境变量 HARNESS_ENV，默认 dev。"""
    env = getattr(args, "env", None) or os.environ.get("HARNESS_ENV")
    return env or "dev"


def cmd_verify(args: argparse.Namespace) -> int:
    """PRE_SPAWN_VERIFY：校验 task 人闸与 Harness 规则，不生成 Prompt。"""
    run_id = uuid.uuid4().hex
    task_path = Path(args.task)
    if not task_path.is_absolute():
        task_path = _repo_root() / task_path
    if not task_path.is_file():
        print(f"BLOCKED: file not found: {task_path}", file=sys.stderr)
        if _audit_enabled(args):
            _log_verify_event(run_id, str(task_path), "PRE_SPAWN_VERIFY", "fail")
        return 2

    errors = validate_task_markdown(task_path)
    if errors:
        print(f"=== {task_path.relative_to(_repo_root())} ===")
        for err in errors:
            print(f"[ERROR] {err}")
        print("BLOCKED")
        if _audit_enabled(args):
            _log_verify_event(run_id, str(task_path), "PRE_SPAWN_VERIFY", "fail")
        return 1

    task = parse_task_markdown(task_path)
    if task.blocks_hat("30") and not task.is_gate_approved("HG-AUDIT-R1"):
        print(f"=== {task_path.relative_to(_repo_root())} ===")
        print("[ERROR] HG-AUDIT-R1 pending but blocks 30 · 禁止派工 30")
        print("BLOCKED")
        if _audit_enabled(args):
            _log_verify_event(run_id, str(task_path), "PRE_SPAWN_VERIFY", "fail")
        return 1

    print(f"=== {task_path.relative_to(_repo_root())} ===")
    print("OK · PRE_SPAWN_VERIFY pass")
    if _audit_enabled(args):
        _log_verify_event(run_id, str(task_path), "PRE_SPAWN_VERIFY", "pass")
    return 0


def _resolve_path(arg: str | None, cfg_key: str) -> Path:
    cfg = _load_config()
    path = Path(arg or cfg.get("probe", {}).get(cfg_key, ""))
    if not path.is_absolute():
        path = _repo_root() / path
    return path


def _build_task_from_args(args: argparse.Namespace) -> tuple[Path, Path]:
    graph_path = _resolve_path(args.graph, "default_graph")
    task_path = Path(args.task)
    if not task_path.is_absolute():
        task_path = _repo_root() / task_path
    return graph_path, task_path


def _apply_task_overrides(task, args: argparse.Namespace):
    if args.entry:
        task.entry_node = args.entry
    if args.hat:
        task.planned_hats = [h.strip() for h in args.hat.split(",")]
    if args.spec:
        task.spec_path = args.spec
    if args.review_target:
        task.review_target = args.review_target
    if args.run_output:
        task.run_output = args.run_output
    if args.mode:
        task.mode = args.mode
    if args.query:
        task.dynamic_query = args.query
    return task


def _persist_run_outputs(runner, run_result, output_dir: Path, *, show_prompt: bool = True) -> None:
    """持久化 run/compile 输出：prompt 文件与 task_run JSON。"""
    compiled_prompts = runner.get_last_prompts()
    for ref, compiled in compiled_prompts.items():
        persist_prompt(output_dir / f"prompt_{ref}.md", compiled)
    if run_result.session_id:
        persist_run_graph(output_dir / f"task_run_{run_result.session_id}.json", run_result)
    if show_prompt:
        for ref, compiled in compiled_prompts.items():
            print(f"\n--- {ref} ---")
            print(compiled.full_text)
            print(f"[static: {compiled.static_char_count}, dynamic: {compiled.dynamic_char_count}]")


def cmd_compile(args: argparse.Namespace) -> int:
    run_id = uuid.uuid4().hex
    graph_path, task_path = _build_task_from_args(args)

    graph = load_graph(graph_path)
    task = parse_task_markdown(task_path, dynamic_query=args.query or "")
    task = _apply_task_overrides(task, args)

    wiki_path = _resolve_path(None, "default_wiki")
    output_dir = _repo_root() / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    runner = TaskRunner(task, graph, load_wiki_stub(wiki_path))
    run_graph = runner.run_sequence()
    _persist_run_outputs(runner, run_graph, output_dir, show_prompt=not args.quiet)
    print("\n✅ compile 完成 · 见 outputs/prompt_*.md 与 task_run_*.json")
    if _audit_enabled(args):
        output_summary = str(output_dir / f"task_run_{run_graph.session_id}.json")
        _log_compile_event(run_id, str(task_path), output_summary)
    return 0


def cmd_graph_query(args: argparse.Namespace) -> int:
    graph_path = _resolve_path(args.graph, "default_graph")
    graph = load_graph(graph_path)
    cfg = ConfigManager.default(project_root=str(_repo_root()))
    depth = args.depth or cfg.get("harness.probe.default_depth", 2)
    result = query_subgraph(graph, args.node, depth=depth)
    print(result.mermaid)
    print(f"\n# nodes ({len(result.node_ids)}): {', '.join(result.node_ids)}")
    return 0


def _resolve_safety_params(args: argparse.Namespace) -> tuple[SafetyConfig, str, str | None]:
    """解析 CLI 与统一配置中心的安全参数，返回 (config, mode, log_dir)。"""
    cfg = ConfigManager.default(
        project_root=str(_repo_root()),
        env=_resolve_env(args),
    )

    safety_mode = getattr(args, "safety_mode", None) or cfg.get("harness.safety.mode", "whitelist")
    execution_log_dir = getattr(args, "execution_log_dir", None)
    if execution_log_dir:
        elp = Path(execution_log_dir)
        if not elp.is_absolute():
            elp = _repo_root() / elp
        execution_log_dir = str(elp)

    safety_config = SafetyConfig.from_config_manager(cfg)
    if getattr(args, "safety_config", None):
        safety_config = load_safety_config(args.safety_config)

    # --capability 显式追加到策略能力集
    if getattr(args, "capability", None):
        extra = CapabilitySet(args.capability)
        safety_config.capabilities = safety_config.capabilities | extra

    if getattr(args, "safety_reload", False):
        if not safety_config.reload():
            warnings.warn(
                f"safety_config_reload_failed or no path: {safety_config.path}",
                stacklevel=2,
            )

    return safety_config, safety_mode, execution_log_dir


def _resolve_executor_plugin_name(args: argparse.Namespace) -> str:
    """解析执行器插件名称。

    优先级：--executor-plugin > --executor 兼容映射 > 配置中心 > 默认。
    """
    cfg = ConfigManager.default(
        project_root=str(_repo_root()),
        env=_resolve_env(args),
    )
    if args.executor_plugin:
        cfg.set("harness.executor.default_plugin", args.executor_plugin)
    else:
        legacy_map = {"mock": "dry-run", "real": "subprocess"}
        if args.executor in legacy_map:
            cfg.set("harness.executor.default_plugin", legacy_map[args.executor])
    return cfg.get("harness.executor.default_plugin", "subprocess")


def _resolve_sandbox_overrides(args: argparse.Namespace) -> dict[str, object]:
    """解析 CLI 传入的沙箱参数覆盖。"""
    overrides: dict[str, object] = {}
    if args.sandbox_image:
        overrides["image"] = args.sandbox_image
    if args.sandbox_timeout:
        overrides["timeout"] = args.sandbox_timeout
    if args.sandbox_no_network:
        overrides["network"] = False
    if args.sandbox_memory:
        overrides["memory"] = args.sandbox_memory
    if getattr(args, "capability", None):
        overrides["capabilities"] = CapabilitySet(args.capability)
    return overrides


def _build_executor(
    plugin_name: str,
    *,
    safety_config: SafetyConfig,
    safety_mode: str,
    execution_log_dir: str | None,
    dry_run: bool,
    sandbox_overrides: dict[str, object] | None = None,
) -> VerifyExecutor:
    """根据插件名称构造配置好的执行器实例。"""
    if plugin_name == "subprocess":
        return SubprocessExecutor(
            safety_mode=safety_mode,
            dry_run=dry_run,
            execution_log_dir=execution_log_dir,
            safety_config=safety_config,
        )
    if plugin_name == "dry-run":
        return DryRunExecutor()
    if plugin_name == "preview":
        return PreviewExecutor(
            safety_mode=safety_mode,
            safety_config=safety_config,
        )
    return load_executor_plugin(plugin_name, **(sandbox_overrides or {}))


def _preview_report_to_dict(report, ref: str) -> dict:
    data = asdict(report)
    data["ref"] = ref
    return data


def _preview_reports_to_json(reports: list[dict]) -> str:
    return json.dumps(reports, ensure_ascii=False, indent=2)


def _preview_reports_to_markdown(reports: list[dict]) -> str:
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
    lines.append("")
    for report in reports:
        lines.append(f"## {report.get('ref', 'command')}")
        lines.append(f"- **command**: `{report['cmd']}`")
        lines.append(f"- **risk_level**: {report['risk_level']}")
        lines.append(f"- **recommended_mode**: {report['recommended_mode']}")
        if report.get("reason"):
            lines.append(f"- **reason**: {report['reason']}")
        lines.append("")
    return "\n".join(lines)


def _generate_preview(
    args: argparse.Namespace,
) -> tuple[list[dict], str]:
    """生成沙箱预览报告。返回 (reports, format)。"""
    safety_config, safety_mode, _ = _resolve_safety_params(args)
    executor = PreviewExecutor(
        safety_mode=safety_mode,
        safety_config=safety_config,
    )

    _, task_path = _build_task_from_args(args)
    task = parse_task_markdown(task_path, dynamic_query=args.query or "")
    task = _apply_task_overrides(task, args)

    # preview 与真实执行互不影响；若用户同时指定 --executor real，给出提示
    if args.executor == "real":
        warnings.warn(
            "--preview takes precedence over --executor real; no command will be executed",
            stacklevel=2,
        )

    reports: list[dict] = []
    for contract in task.contracts:
        report = executor.preview(contract.verify)
        reports.append(_preview_report_to_dict(report, contract.ref))

    return reports, args.preview_format


def cmd_run(args: argparse.Namespace) -> int:
    if args.preview:
        reports, fmt = _generate_preview(args)
        if fmt == "markdown":
            print(_preview_reports_to_markdown(reports))
        else:
            print(_preview_reports_to_json(reports))
        return 0

    graph_path, task_path = _build_task_from_args(args)

    graph = load_graph(graph_path)
    task = parse_task_markdown(task_path, dynamic_query=args.query or "")
    task = _apply_task_overrides(task, args)

    wiki_path = _resolve_path(None, "default_wiki")
    output_dir = _repo_root() / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    executor = None
    plugin_name = _resolve_executor_plugin_name(args)
    if plugin_name != "none":
        safety_config, safety_mode, execution_log_dir = _resolve_safety_params(args)
        sandbox_overrides = _resolve_sandbox_overrides(args)
        executor = _build_executor(
            plugin_name,
            safety_config=safety_config,
            safety_mode=safety_mode,
            execution_log_dir=execution_log_dir,
            dry_run=args.dry_run,
            sandbox_overrides=sandbox_overrides,
        )

    cwd = None
    if args.cwd:
        cwd_path = Path(args.cwd)
        if not cwd_path.is_dir():
            print(f"BLOCKED: --cwd not found or not a directory: {args.cwd}", file=sys.stderr)
            return 2
        cwd = str(cwd_path.resolve())

    runner = TaskRunner(task, graph, load_wiki_stub(wiki_path), executor=executor, cwd=cwd)
    start = time.time()
    run_result = runner.run_sequence(
        from_hat=args.from_hat,
        to_hat=args.to_hat,
        max_retries=args.max_retries,
    )
    duration_ms = int((time.time() - start) * 1000)
    _persist_run_outputs(runner, run_result, output_dir, show_prompt=not args.quiet)
    print(f"\n✅ run 完成 · session={run_result.session_id} · status={run_result.status}")
    print(f"   nodes: {[(n.hat, n.status.value) for n in run_result.nodes]}")
    print(f"   见 outputs/prompt_*.md 与 outputs/task_run_{run_result.session_id}.json")
    if _audit_enabled(args):
        hats = [n.hat for n in run_result.nodes]
        _log_run_event(
            run_id=run_result.session_id,
            task_path=str(task_path),
            hats=hats,
            executor_plugin=plugin_name,
            result_status=str(run_result.status),
            duration_ms=duration_ms,
        )
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    """监视 freeze_id 漂移。"""
    graph_path = _resolve_path(args.graph, "default_graph")
    task_path = Path(args.task)
    if not task_path.is_absolute():
        task_path = _repo_root() / task_path
    snapshot = load_graph(graph_path)
    baseline = {node.id: node.freeze_id for node in snapshot.nodes}

    if args.once:
        drift = _detect_drift(baseline, task_path)
        if drift:
            print("DRIFT detected:", drift)
            return 1
        print("OK · no drift")
        return 0

    try:
        while True:
            drift = _detect_drift(baseline, task_path)
            if drift:
                print("DRIFT:", drift)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nwatch stopped")
        return 0


def _detect_drift(baseline: dict[str, str], task_path: Path) -> list[str]:
    """比对当前任务文件中的 freeze_id 与基线。"""
    if not task_path.is_file():
        return [f"task file missing: {task_path}"]
    task = parse_task_markdown(task_path)
    drift: list[str] = []
    for node in task.required_nodes:
        current = node.freeze_id
        expected = baseline.get(node.id)
        if expected and current != expected:
            drift.append(f"{node.id}: {expected} -> {current}")
    return drift


def cmd_mcp(args: argparse.Namespace) -> int:
    """启动 MCP Server。"""
    try:
        from harness_probe.mcp.server import run_server
    except ImportError as exc:
        print(f"MCP server not available: {exc}", file=sys.stderr)
        return 2
    return run_server(args)


def cmd_audit_list(args: argparse.Namespace) -> int:
    reader = AuditReader()
    runs = reader.list_runs(
        task=args.task,
        hat=args.hat,
        executor_plugin=args.executor_plugin,
        since=args.since,
        limit=args.limit,
    )
    if not runs:
        print("No audit runs found.")
        return 0
    for run in runs:
        print(f"{run['run_id']}\t{run.get('event_type', '-')}\t{run['task']}\t{run['hat'] or '-'}\t{run['result']}")
    return 0


def cmd_audit_show(args: argparse.Namespace) -> int:
    reader = AuditReader()
    run = reader.get_run(args.run_id)
    if run is None:
        print(f"audit run not found: {args.run_id}", file=sys.stderr)
        return 1
    print(json.dumps(run, indent=2, ensure_ascii=False))
    return 0


def cmd_audit_report(args: argparse.Namespace) -> int:
    reader = AuditReader()
    report = AuditReport(
        reader=reader,
        task=args.task,
        since=args.since,
    )
    text = report.to_json() if args.format == "json" else report.to_markdown()
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"audit report written to {args.output}")
    else:
        print(text)
    return 0


def cmd_audit_config(args: argparse.Namespace) -> int:
    cfg = ConfigManager.default(project_root=str(_repo_root()))
    logger = AuditLogger(config=cfg)
    print(json.dumps({
        "log_dir": str(logger.get_log_dir()),
        "retention": cfg.get("harness.audit.retention", {}),
    }, indent=2, ensure_ascii=False))
    return 0


def cmd_safety_show(args: argparse.Namespace) -> int:
    """显示当前安全策略与能力模型。"""
    safety_config, _safety_mode, _log_dir = _resolve_safety_params(args)

    if getattr(args, "format", "markdown") == "json":
        print(
            json.dumps(
                {
                    "mode": safety_config.mode.value,
                    "allowed_commands": safety_config.allowed_commands,
                    "dangerous_metacharacters": safety_config.dangerous_metacharacters,
                    "dangerous_prefixes": safety_config.dangerous_prefixes,
                    "max_command_length": safety_config.max_command_length,
                    "capabilities": safety_config.capabilities.to_list(),
                    "source": safety_config.path,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    lines = [
        "# Harness Probe · 当前安全策略",
        "",
        f"- **mode**: `{safety_config.mode.value}`",
        f"- **max_command_length**: {safety_config.max_command_length}",
        f"- **capabilities**: {', '.join(safety_config.capabilities.to_list())}",
        f"- **source**: `{safety_config.path or 'default'}`",
        "",
        "## allowed_commands",
        "",
    ]
    for cmd in safety_config.allowed_commands:
        lines.append(f"- `{cmd}`")
    lines.extend(["", "## dangerous_metacharacters", ""])
    for token in safety_config.dangerous_metacharacters:
        lines.append(f"- `{token}`")
    lines.extend(["", "## dangerous_prefixes", ""])
    for prefix in safety_config.dangerous_prefixes:
        lines.append(f"- `{prefix}`")
    print("\n".join(lines))
    return 0


def cmd_safety_evaluate(args: argparse.Namespace) -> int:
    """评估命令风险等级。"""
    safety_config, _safety_mode, _log_dir = _resolve_safety_params(args)
    cmd = " ".join(args.cmd)
    risk, required, missing, reason = evaluate_command_risk(
        cmd, safety_config.capabilities
    )
    print(
        json.dumps(
            {
                "cmd": cmd,
                "risk": risk.value,
                "required_capabilities": required.to_list(),
                "granted_capabilities": safety_config.capabilities.to_list(),
                "missing_capabilities": missing.to_list(),
                "reason": reason,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _render_config_markdown(cfg: ConfigManager) -> str:
    lines = ["# Harness Probe · 当前合并配置", "", "| 键 | 值 |", "|---|---|"]

    def _walk(data: dict, prefix: str) -> None:
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                _walk(value, path)
            else:
                lines.append(f"| `{path}` | `{value!r}` |")

    _walk(cfg.to_dict(), "")
    return "\n".join(lines)


def cmd_config_validate(args: argparse.Namespace) -> int:
    """校验当前配置并返回退出码。"""
    try:
        cfg = ConfigManager.default(
            config_dir=args.config_dir,
            project_root=str(_repo_root()),
            env=_resolve_env(args),
        )
    except ConfigError as exc:
        print(f"config_error: {exc}", file=sys.stderr)
        return 2

    errors = cfg.validate()
    if errors:
        for err in errors:
            print(f"[ERROR] {err}")
        return 2

    print("OK · configuration valid")
    return 0


def cmd_config_show(args: argparse.Namespace) -> int:
    """输出当前合并后的配置。"""
    try:
        cfg = ConfigManager.default(
            config_dir=args.config_dir,
            project_root=str(_repo_root()),
            env=_resolve_env(args),
        )
    except ConfigError as exc:
        print(f"config_error: {exc}", file=sys.stderr)
        return 2

    fmt = args.format
    if fmt == "json":
        print(json.dumps(cfg.to_dict(), indent=2, ensure_ascii=False))
    elif fmt == "yaml":
        print(yaml.safe_dump(cfg.to_dict(), sort_keys=False, allow_unicode=True))
    else:  # markdown
        print(_render_config_markdown(cfg))
    return 0


def cmd_config_watch(args: argparse.Namespace) -> int:
    """启动配置热重载监听。"""
    try:
        cfg = ConfigManager.default(
            config_dir=args.config_dir,
            project_root=str(_repo_root()),
            env=_resolve_env(args),
        )
    except ConfigError as exc:
        print(f"config_error: {exc}", file=sys.stderr)
        return 2

    def _on_reload(manager: ConfigManager) -> None:
        print("[reload] configuration reloaded")
        if args.verbose:
            print(yaml.safe_dump(manager.to_dict(), sort_keys=False, allow_unicode=True))

    cfg.register_on_reload(_on_reload)
    cfg.watch()
    print(f"watching config dir: {cfg._config_dir}")
    print("press Ctrl+C to stop")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        cfg.stop_watch()
        print("\nwatch stopped")
    return 0


_GATE_COMPLETED_RE = re.compile(
    r"^\|\s*(?P<gate_id>HG-[A-Z0-9-]+)\s*\|\s*`?completed`?\s*\|",
    re.MULTILINE,
)


def _collect_task_validate_errors(path: Path, strict: bool) -> tuple[list[str], list[str]]:
    """校验单个任务单，返回 (errors, warnings)。"""
    errors: list[str] = []
    warnings_list: list[str] = []
    try:
        schema, warns = parse_task_file(path)
    except ValidationError as exc:
        for err in exc.errors():
            loc = ".".join(str(item) for item in err["loc"])
            errors.append(f"{loc}: {err['msg']}")
        return errors, warnings_list
    except ValueError as exc:
        errors.append(f"parse_error: {exc}")
        return errors, warnings_list

    warnings_list.extend(warns)

    # 人闸阻塞 30
    for gate in schema.blocking_gates("30"):
        errors.append(
            f"HUMAN-GATE-BLOCKS-30: {gate.gate_id} status={gate.status.value} "
            f"blocks_hats={gate.blocks_hats}"
        )

    # --strict 模式下 completed 非法
    if strict:
        text = path.read_text(encoding="utf-8")
        for match in _GATE_COMPLETED_RE.finditer(text):
            errors.append(
                f"STRICT-COMPLETED-ILLEGAL: gate {match.group('gate_id')} "
                "uses deprecated status 'completed', use 'approved'"
            )

    return errors, warnings_list


def _relative_task_path(path: Path) -> Path:
    if path.is_absolute():
        try:
            return path.relative_to(_repo_root())
        except ValueError:
            pass
    return path


def _format_task_results_markdown(results: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for r in results:
        rel = _relative_task_path(Path(r["path"]))
        lines.append(f"=== {rel} ===")
        if r["ok"] and not r["warnings"]:
            lines.append("OK · task schema valid")
        else:
            for w in r["warnings"]:
                lines.append(f"[WARN] {w}")
            for e in r["errors"]:
                lines.append(f"[ERROR] {e}")
            lines.append("FAIL" if r["errors"] else "OK (warnings)")
    return "\n".join(lines)


def _format_task_results_json(results: list[dict[str, Any]]) -> str:
    payload = []
    for r in results:
        payload.append(
            {
                "path": str(_relative_task_path(Path(r["path"]))),
                "ok": r["ok"],
                "errors": r["errors"],
                "warnings": r["warnings"],
            }
        )
    return json.dumps(payload, ensure_ascii=False, indent=2)


def cmd_task_validate(args: argparse.Namespace) -> int:
    """校验任务单 Schema 与人闸。"""
    if args.task and args.dir:
        print("specify either --task or --dir, not both", file=sys.stderr)
        return 2
    if not args.task and not args.dir:
        print("specify --task <path> or --dir <dir>", file=sys.stderr)
        return 2

    paths: list[Path] = []
    if args.task:
        p = Path(args.task)
        if not p.is_absolute():
            p = _repo_root() / p
        paths.append(p)
    else:
        d = Path(args.dir)
        if not d.is_absolute():
            d = _repo_root() / d
        if not d.is_dir():
            print(f"dir not found: {d}", file=sys.stderr)
            return 2
        paths = sorted(d.glob("task_*.md"))
        if not paths:
            print(f"no task_*.md files found in {d}", file=sys.stderr)
            return 2

    results: list[dict[str, Any]] = []
    for p in paths:
        if not p.is_file():
            results.append(
                {
                    "path": str(p),
                    "ok": False,
                    "errors": ["file not found"],
                    "warnings": [],
                }
            )
            continue
        errors, warnings_list = _collect_task_validate_errors(p, strict=args.strict)
        results.append(
            {
                "path": str(p),
                "ok": not errors,
                "errors": errors,
                "warnings": warnings_list,
            }
        )

    if args.format == "json":
        print(_format_task_results_json(results))
    else:
        print(_format_task_results_markdown(results))

    if any(not r["ok"] for r in results):
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Harness Probe · L0/L1/L1.5/L2 探针")
    sub = parser.add_subparsers(dest="command", required=True)

    p_verify = sub.add_parser("verify", help="PRE_SPAWN_VERIFY · 校验 task 人闸与规则")
    p_verify.add_argument("--task", default="data/tasks/sample_task.md")
    p_verify.add_argument("--no-audit", action="store_true", help="禁用审计日志")
    p_verify.set_defaults(func=cmd_verify)

    p_compile = sub.add_parser("compile", help="编译 Prompt + L1.5 快照（dry-run）")
    p_compile.add_argument("--task", default="data/tasks/sample_task.md")
    p_compile.add_argument("--graph", default=None)
    p_compile.add_argument("--entry", default=None, help="覆盖 task entry_node")
    p_compile.add_argument("--hat", default=None, help="指定帽子，逗号分隔，如 10-spec,20-review,30,40")
    p_compile.add_argument("--spec", default=None, help="10-task 关联的 SPEC 文件路径")
    p_compile.add_argument("--review-target", default=None, choices=["task", "spec"], help="20-review 审核对象")
    p_compile.add_argument("--run-output", default=None, help="50-reinspect 关联的 task_run JSON 路径")
    p_compile.add_argument("--mode", default=None, choices=["independent", "global"], help="50-reinspect 模式")
    p_compile.add_argument("--query", default=None)
    p_compile.add_argument("--quiet", action="store_true")
    p_compile.add_argument("--no-audit", action="store_true", help="禁用审计日志")
    p_compile.add_argument(
        "--env",
        "-e",
        default=None,
        help="目标环境（如 dev/test/prod），默认 dev",
    )
    p_compile.add_argument(
        "--capability",
        action="append",
        default=[],
        help="显式声明额外能力（可多次指定）",
    )
    p_compile.set_defaults(func=cmd_compile)

    p_run = sub.add_parser("run", help="模拟执行多帽序列（dry-run）")
    p_run.add_argument("--task", default="data/tasks/sample_task.md")
    p_run.add_argument("--graph", default=None)
    p_run.add_argument("--entry", default=None)
    p_run.add_argument("--hat", default=None, help="指定帽子，逗号分隔")
    p_run.add_argument("--from-hat", default=None, help="起始帽子，如 10-spec")
    p_run.add_argument("--to-hat", default=None, help="结束帽子，如 50-reinspect")
    p_run.add_argument("--spec", default=None)
    p_run.add_argument("--review-target", default=None, choices=["task", "spec"])
    p_run.add_argument("--run-output", default=None)
    p_run.add_argument("--mode", default=None, choices=["independent", "global"])
    p_run.add_argument("--query", default=None)
    p_run.add_argument("--quiet", action="store_true")
    p_run.add_argument(
        "--executor",
        default="mock",
        choices=["mock", "real"],
        help="执行器类型：mock 为 dry-run（默认），real 真实执行 contract.verify",
    )
    p_run.add_argument(
        "--executor-plugin",
        default=None,
        choices=["dry-run", "preview", "subprocess", "docker", "firejail"],
        help="插件化执行器：dry-run / preview / subprocess / docker / firejail",
    )
    p_run.add_argument(
        "--sandbox-image",
        default=None,
        help="沙箱镜像，仅对 docker/firejail 生效",
    )
    p_run.add_argument(
        "--sandbox-timeout",
        type=float,
        default=None,
        help="沙箱命令超时秒数，默认读取 config/executor.yaml",
    )
    p_run.add_argument(
        "--sandbox-no-network",
        action="store_true",
        help="禁用沙箱网络，仅对 docker/firejail 生效",
    )
    p_run.add_argument(
        "--sandbox-memory",
        default=None,
        help="沙箱内存限制，如 512m / 1g",
    )
    p_run.add_argument(
        "--max-retries",
        type=int,
        default=0,
        help="contract 失败时最大重试次数，默认 0",
    )
    p_run.add_argument(
        "--cwd",
        default=None,
        help="真实执行时的工作目录，默认使用当前目录",
    )
    p_run.add_argument(
        "--dry-run",
        action="store_true",
        help="不实际执行 contract.verify，仅输出预览",
    )
    p_run.add_argument(
        "--safety-mode",
        default=None,
        choices=["whitelist", "audit", "unsafe"],
        help="安全执行模式：whitelist（默认）/ audit / unsafe",
    )
    p_run.add_argument(
        "--execution-log-dir",
        default=None,
        help="执行/拦截事件日志目录，默认不写入",
    )
    p_run.add_argument(
        "--safety-config",
        default=None,
        help="安全策略 YAML 路径，与默认配置合并",
    )
    p_run.add_argument(
        "--safety-reload",
        action="store_true",
        help="运行时重新加载安全策略文件",
    )
    p_run.add_argument("--no-audit", action="store_true", help="禁用审计日志")
    p_run.add_argument(
        "--capability",
        action="append",
        default=[],
        help="显式声明额外能力（可多次指定）",
    )
    p_run.add_argument(
        "--preview",
        action="store_true",
        help="不执行命令，仅输出沙箱影响报告",
    )
    p_run.add_argument(
        "--preview-format",
        default="json",
        choices=["json", "markdown"],
        help="沙箱预览报告格式：json（默认）/ markdown",
    )
    p_run.add_argument(
        "--env",
        "-e",
        default=None,
        help="目标环境（如 dev/test/prod），默认 dev",
    )
    p_run.set_defaults(func=cmd_run)

    p_watch = sub.add_parser("watch", help="监视 freeze_id 漂移")
    p_watch.add_argument("--graph", default=None)
    p_watch.add_argument("--task", default="data/tasks/sample_task.md")
    p_watch.add_argument("--entry", default=None, help="影响分析入口节点")
    p_watch.add_argument("--interval", type=int, default=5, help="轮询秒数，默认 5")
    p_watch.add_argument("--once", action="store_true", help="只检测一次")
    p_watch.set_defaults(func=cmd_watch)

    p_gq = sub.add_parser("graph-query", help="L0 子图查询")
    p_gq.add_argument("--node", required=True)
    p_gq.add_argument("--graph", default=None)
    p_gq.add_argument("--depth", type=int, default=None)
    p_gq.set_defaults(func=cmd_graph_query)

    p_mcp = sub.add_parser("mcp", help="启动 MCP Server")
    p_mcp.add_argument("--config", default=None, help="probe config yaml path")
    p_mcp.add_argument("--transport", default="stdio", choices=["stdio", "sse"], help="MCP transport")
    p_mcp.add_argument("--port", type=int, default=8080, help="SSE port")
    p_mcp.set_defaults(func=cmd_mcp)

    p_audit = sub.add_parser("audit", help="审计日志管理")
    audit_sub = p_audit.add_subparsers(dest="audit_command", required=True)

    p_audit_list = audit_sub.add_parser("list", help="列出历史运行")
    p_audit_list.add_argument("--task", default=None, help="按 task 路径过滤")
    p_audit_list.add_argument("--hat", default=None, help="按 hat 过滤")
    p_audit_list.add_argument("--executor-plugin", default=None, help="按执行器插件过滤")
    p_audit_list.add_argument("--since", default=None, help="按时间过滤（ISO 日期或相对时间如 1d, 7d）")
    p_audit_list.add_argument("--limit", type=int, default=20, help="限制数量，默认 20")
    p_audit_list.set_defaults(func=cmd_audit_list)

    p_audit_show = audit_sub.add_parser("show", help="显示单次运行详情")
    p_audit_show.add_argument("--run-id", required=True, help="运行 ID")
    p_audit_show.set_defaults(func=cmd_audit_show)

    p_audit_report = audit_sub.add_parser("report", help="生成审计报告")
    p_audit_report.add_argument("--task", default=None, help="按 task 过滤")
    p_audit_report.add_argument("--since", default=None, help="按时间过滤")
    p_audit_report.add_argument("--format", default="markdown", choices=["json", "markdown"], help="报告格式")
    p_audit_report.add_argument("--output", default=None, help="输出文件，默认 stdout")
    p_audit_report.set_defaults(func=cmd_audit_report)

    p_audit_config = audit_sub.add_parser("config", help="显示审计配置")
    p_audit_config.set_defaults(func=cmd_audit_config)

    p_config = sub.add_parser("config", help="配置中心")
    config_sub = p_config.add_subparsers(dest="config_command", required=True)

    p_config_validate = config_sub.add_parser("validate", help="校验配置并返回退出码")
    p_config_validate.add_argument(
        "--config-dir",
        default=None,
        help="配置目录，默认使用 <repo>/config",
    )
    p_config_validate.add_argument(
        "--env",
        "-e",
        default=None,
        help="目标环境（如 dev/test/prod），默认 dev",
    )
    p_config_validate.set_defaults(func=cmd_config_validate)

    p_config_show = config_sub.add_parser("show", help="显示合并后的配置")
    p_config_show.add_argument(
        "--config-dir",
        default=None,
        help="配置目录，默认使用 <repo>/config",
    )
    p_config_show.add_argument(
        "--env",
        "-e",
        default=None,
        help="目标环境（如 dev/test/prod），默认 dev",
    )
    p_config_show.add_argument(
        "--format",
        default="json",
        choices=["json", "yaml", "markdown"],
        help="输出格式：json（默认）/ yaml / markdown",
    )
    p_config_show.set_defaults(func=cmd_config_show)

    p_config_watch = config_sub.add_parser("watch", help="启动配置热重载监听")
    p_config_watch.add_argument(
        "--config-dir",
        default=None,
        help="配置目录，默认使用 <repo>/config",
    )
    p_config_watch.add_argument(
        "--env",
        "-e",
        default=None,
        help="目标环境（如 dev/test/prod），默认 dev",
    )
    p_config_watch.add_argument(
        "--verbose",
        action="store_true",
        help="重载后打印完整配置",
    )
    p_config_watch.set_defaults(func=cmd_config_watch)

    p_task = sub.add_parser("task", help="任务单 Schema 校验")
    task_sub = p_task.add_subparsers(dest="task_command", required=True)

    p_task_validate = task_sub.add_parser("validate", help="校验任务单 Schema 与人闸")
    p_task_validate.add_argument(
        "--task",
        default=None,
        help="任务单 Markdown 文件路径",
    )
    p_task_validate.add_argument(
        "--dir",
        default=None,
        help="批量扫描目录下的 task_*.md",
    )
    p_task_validate.add_argument(
        "--format",
        default="markdown",
        choices=["json", "markdown"],
        help="输出格式：markdown（默认）/ json",
    )
    p_task_validate.add_argument(
        "--strict",
        action="store_true",
        help="将 completed 人闸状态视为非法",
    )
    p_task_validate.set_defaults(func=cmd_task_validate)

    p_safety = sub.add_parser("safety", help="安全策略与能力模型")
    safety_sub = p_safety.add_subparsers(dest="safety_command", required=True)

    p_safety_show = safety_sub.add_parser("show", help="显示当前安全策略与能力模型")
    p_safety_show.add_argument(
        "--safety-config",
        default=None,
        help="安全策略 YAML 路径，与默认配置合并",
    )
    p_safety_show.add_argument(
        "--safety-reload",
        action="store_true",
        help="运行时重新加载安全策略文件",
    )
    p_safety_show.add_argument(
        "--capability",
        action="append",
        default=[],
        help="显式声明额外能力（可多次指定）",
    )
    p_safety_show.add_argument(
        "--format",
        default="markdown",
        choices=["json", "markdown"],
        help="输出格式：markdown（默认）/ json",
    )
    p_safety_show.add_argument(
        "--env",
        "-e",
        default=None,
        help="目标环境（如 dev/test/prod），默认 dev",
    )
    p_safety_show.set_defaults(func=cmd_safety_show)

    p_safety_evaluate = safety_sub.add_parser("evaluate", help="评估命令风险等级")
    p_safety_evaluate.add_argument(
        "cmd",
        nargs="+",
        help="要评估的命令（多个参数将用空格连接）",
    )
    p_safety_evaluate.add_argument(
        "--safety-config",
        default=None,
        help="安全策略 YAML 路径，与默认配置合并",
    )
    p_safety_evaluate.add_argument(
        "--safety-reload",
        action="store_true",
        help="运行时重新加载安全策略文件",
    )
    p_safety_evaluate.add_argument(
        "--capability",
        action="append",
        default=[],
        help="显式声明额外能力（可多次指定）",
    )
    p_safety_evaluate.add_argument(
        "--env",
        "-e",
        default=None,
        help="目标环境（如 dev/test/prod），默认 dev",
    )
    p_safety_evaluate.set_defaults(func=cmd_safety_evaluate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:  # noqa: BLE001 — CLI 统一报错
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
