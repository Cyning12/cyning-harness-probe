"""Harness Probe CLI"""

from __future__ import annotations

import argparse
import sys
import time
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
from harness_sdk import TaskRunner
from harness_sdk.executor import SubprocessExecutor
from harness_sdk.graph import query_subgraph


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_config() -> dict:
    cfg_path = _repo_root() / "config" / "probe_config.yaml"
    if not cfg_path.exists():
        return {}
    return yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}


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
    cfg = _load_config()
    depth = args.depth or cfg.get("probe", {}).get("default_depth", 2)
    result = query_subgraph(graph, args.node, depth=depth)
    print(result.mermaid)
    print(f"\n# nodes ({len(result.node_ids)}): {', '.join(result.node_ids)}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    graph_path, task_path = _build_task_from_args(args)

    graph = load_graph(graph_path)
    task = parse_task_markdown(task_path, dynamic_query=args.query or "")
    task = _apply_task_overrides(task, args)

    wiki_path = _resolve_path(None, "default_wiki")
    output_dir = _repo_root() / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    executor = None
    if args.executor == "real":
        executor = SubprocessExecutor()

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
