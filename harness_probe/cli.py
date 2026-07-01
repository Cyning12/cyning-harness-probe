"""Harness Probe CLI"""

from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from dataclasses import asdict
from pathlib import Path

import yaml

from harness_probe.io import (
    load_graph,
    load_wiki_stub,
    parse_task_markdown,
    persist_prompt,
    persist_run_graph,
    validate_task_markdown,
)
from harness_probe.rendering import print_cache_boundary
from harness_sdk import ConfigError, ConfigManager, TaskRunner
from harness_sdk.executor import (
    DryRunExecutor,
    PreviewExecutor,
    SubprocessExecutor,
    VerifyExecutor,
    load_executor_plugin,
)
from harness_sdk.graph import query_subgraph
from harness_sdk.safety import SafetyConfig, load_safety_config


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def cmd_verify(args: argparse.Namespace) -> int:
    """PRE_SPAWN_VERIFY：校验 task 人闸与 Harness 规则，不生成 Prompt。"""
    task_path = Path(args.task)
    if not task_path.is_absolute():
        task_path = _repo_root() / task_path
    if not task_path.is_file():
        print(f"BLOCKED: file not found: {task_path}", file=sys.stderr)
        return 2

    errors = validate_task_markdown(task_path)
    if errors:
        print(f"=== {task_path.relative_to(_repo_root())} ===")
        for err in errors:
            print(f"[ERROR] {err}")
        print("BLOCKED")
        return 1

    task = parse_task_markdown(task_path)
    if task.blocks_hat("30") and not task.is_gate_approved("HG-AUDIT-R1"):
        print(f"=== {task_path.relative_to(_repo_root())} ===")
        print("[ERROR] HG-AUDIT-R1 pending but blocks 30 · 禁止派工 30")
        print("BLOCKED")
        return 1

    print(f"=== {task_path.relative_to(_repo_root())} ===")
    print("OK · PRE_SPAWN_VERIFY pass")
    return 0


def _resolve_path(arg: str | None, cfg_key: str) -> Path:
    cfg = ConfigManager.default(project_root=str(_repo_root()))
    value = arg or cfg.get(f"harness.probe.{cfg_key}", "")
    path = Path(value)
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
        task = task.model_copy(update={"entry_node": args.entry})
    if args.hat:
        task = task.model_copy(update={"planned_hats": args.hat.split(",")})
    if args.spec:
        spec_path = Path(args.spec)
        if not spec_path.is_absolute():
            spec_path = _repo_root() / spec_path
        spec_text = spec_path.read_text(encoding="utf-8") if spec_path.exists() else ""
        task = task.model_copy(update={"spec_path": str(args.spec), "spec_text": spec_text})
    if args.review_target:
        task = task.model_copy(update={"review_target": args.review_target})
    if args.run_output:
        task = task.model_copy(update={"run_output_path": args.run_output})
    if args.mode:
        task = task.model_copy(update={"reinspect_mode": args.mode})
    return task


def _persist_run_outputs(
    runner: TaskRunner,
    run_graph,
    output_dir: Path,
    show_prompt: bool,
) -> None:
    session_id = run_graph.session_id
    for hat, compiled in runner.get_last_prompts().items():
        prompt_path = output_dir / f"prompt_{session_id}_hat{hat}.md"
        persist_prompt(prompt_path, compiled)
        if show_prompt:
            print(f"\n--- hat {hat} · {prompt_path} ---")
            print_cache_boundary(compiled)

    run_path = output_dir / f"task_run_{session_id}.json"
    persist_run_graph(run_path, run_graph)


def cmd_compile(args: argparse.Namespace) -> int:
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
    cfg = ConfigManager.default(project_root=str(_repo_root()))

    safety_mode = args.safety_mode or cfg.get("harness.safety.mode", "whitelist")
    execution_log_dir = args.execution_log_dir
    if execution_log_dir:
        elp = Path(execution_log_dir)
        if not elp.is_absolute():
            elp = _repo_root() / elp
        execution_log_dir = str(elp)

    safety_config = SafetyConfig.from_config_manager(cfg)
    if args.safety_config:
        safety_config = load_safety_config(args.safety_config)

    if args.safety_reload:
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
    cfg = ConfigManager.default(project_root=str(_repo_root()))
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
    run_result = runner.run_sequence(
        from_hat=args.from_hat,
        to_hat=args.to_hat,
        max_retries=args.max_retries,
    )
    _persist_run_outputs(runner, run_result, output_dir, show_prompt=not args.quiet)
    print(f"\n✅ run 完成 · session={run_result.session_id} · status={run_result.status}")
    print(f"   nodes: {[(n.hat, n.status.value) for n in run_result.nodes]}")
    print(f"   见 outputs/prompt_*.md 与 outputs/task_run_{run_result.session_id}.json")
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    """监视 freeze_id 漂移。"""
    graph_path = _resolve_path(args.graph, "default_graph")
    task_path = Path(args.task)
    if not task_path.is_absolute():
        task_path = _repo_root() / task_path
    interval = args.interval

    while True:
        graph = load_graph(graph_path)
        task = parse_task_markdown(task_path)
        graph_freeze = graph.freeze_id
        task_freeze = task.freeze_id or "（未设置）"
        consistent = graph_freeze == task_freeze

        impacted = []
        if not consistent and args.entry:
            sub = query_subgraph(graph, args.entry, depth=1)
            impacted = sub.node_ids

        print(f"[{time.strftime('%H:%M:%S')}] "
              f"graph={graph_freeze} task={task_freeze} "
              f"{'✅ 一致' if consistent else '⚠️ 漂移'}")
        if not consistent:
            print(f"    影响节点: {', '.join(impacted) if impacted else '(未指定 --entry)'}")
            print(f"    建议: harness verify --impact {args.entry or '?'}")

        if args.once:
            return 0 if consistent else 1

        time.sleep(interval)


def cmd_mcp(args: argparse.Namespace) -> int:
    """启动 MCP Server。"""
    from harness_mcp.server import main as mcp_main

    return mcp_main([
        "--config", args.config or "",
        "--transport", args.transport,
        "--port", str(args.port),
    ])


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Harness Probe · L0/L1/L1.5/L2 探针")
    sub = parser.add_subparsers(dest="command", required=True)

    p_verify = sub.add_parser("verify", help="PRE_SPAWN_VERIFY · 校验 task 人闸与规则")
    p_verify.add_argument("--task", default="data/tasks/sample_task.md")
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
        help="在构建 executor 前重新加载 --safety-config 指定的策略文件",
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

    p_config = sub.add_parser("config", help="配置中心")
    config_sub = p_config.add_subparsers(dest="config_command", required=True)

    p_config_validate = config_sub.add_parser("validate", help="校验配置并返回退出码")
    p_config_validate.add_argument(
        "--config-dir",
        default=None,
        help="配置目录，默认使用 <repo>/config",
    )
    p_config_validate.set_defaults(func=cmd_config_validate)

    p_config_show = config_sub.add_parser("show", help="显示合并后的配置")
    p_config_show.add_argument(
        "--config-dir",
        default=None,
        help="配置目录，默认使用 <repo>/config",
    )
    p_config_show.add_argument(
        "--format",
        default="json",
        choices=["json", "yaml", "markdown"],
        help="输出格式：json（默认）/ yaml / markdown",
    )
    p_config_show.set_defaults(func=cmd_config_show)

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
