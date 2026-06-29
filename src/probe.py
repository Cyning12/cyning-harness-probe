"""Harness Probe CLI"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from src.compiler import parse_task_markdown, validate_task_markdown
from src.graph_loader import load_graph, query_subgraph
from src.orchestrator import HarnessProbeCore


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


def cmd_compile(args: argparse.Namespace) -> int:
    cfg = _load_config()
    graph_path = Path(args.graph or cfg.get("probe", {}).get("default_graph", ""))
    if not graph_path.is_absolute():
        graph_path = _repo_root() / graph_path
    task_path = Path(args.task)
    if not task_path.is_absolute():
        task_path = _repo_root() / task_path

    graph = load_graph(graph_path)
    task = parse_task_markdown(task_path, dynamic_query=args.query or "")
    if args.entry:
        task = task.model_copy(update={"entry_node": args.entry})

    core = HarnessProbeCore(
        graph,
        _repo_root() / cfg.get("probe", {}).get("default_wiki", "data/wiki/syntheses_stub.json"),
        output_dir=_repo_root() / "outputs",
    )
    core.run_task(task, dry_run=True, show_prompt=not args.quiet)
    print("\n✅ compile 完成 · 见 outputs/prompt_*.md 与 task_run_*.json")
    return 0


def cmd_graph_query(args: argparse.Namespace) -> int:
    cfg = _load_config()
    graph_path = Path(args.graph or cfg.get("probe", {}).get("default_graph", ""))
    if not graph_path.is_absolute():
        graph_path = _repo_root() / graph_path
    graph = load_graph(graph_path)
    depth = args.depth or cfg.get("probe", {}).get("default_depth", 2)
    result = query_subgraph(graph, args.node, depth=depth)
    print(result.mermaid)
    print(f"\n# nodes ({len(result.node_ids)}): {', '.join(result.node_ids)}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    return cmd_compile(args)


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
    p_compile.add_argument("--query", default=None)
    p_compile.add_argument("--quiet", action="store_true")
    p_compile.set_defaults(func=cmd_compile)

    p_run = sub.add_parser("run", help="同 compile（默认 dry-run）")
    p_run.add_argument("--task", default="data/tasks/sample_task.md")
    p_run.add_argument("--graph", default=None)
    p_run.add_argument("--entry", default=None)
    p_run.add_argument("--query", default=None)
    p_run.add_argument("--quiet", action="store_true")
    p_run.set_defaults(func=cmd_run)

    p_gq = sub.add_parser("graph-query", help="L0 子图查询")
    p_gq.add_argument("--node", required=True)
    p_gq.add_argument("--graph", default=None)
    p_gq.add_argument("--depth", type=int, default=None)
    p_gq.set_defaults(func=cmd_graph_query)

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
