"""KV-Cache 友好的 Prompt 三段式组装"""

from __future__ import annotations

from src.compiler import format_contract_table, format_wiki_context
from src.models import AcceptanceContract, CompiledPrompt, HarnessTask, SubgraphResult, TechGraph, WikiEntry


def build_subagent_prompt(
    graph: TechGraph,
    task: HarnessTask,
    hat: str,
    subgraph: SubgraphResult,
    wiki_entries: list[WikiEntry],
) -> CompiledPrompt:
    freeze = task.freeze_id or graph.freeze_id
    wiki_block = format_wiki_context(wiki_entries)
    contract_table = format_contract_table(task.contracts)

    static_prefix = f"""# [HARNESS PROBE] System · freeze_id: {freeze}

## L0 · 业务拓扑（局部子图 · depth={subgraph.depth} · entry={subgraph.entry_node}）

```mermaid
{subgraph.mermaid}
```

节点 id 列表：{", ".join(subgraph.node_ids)}

## L2 · 冷记忆摘要（合成 · 非 invoke 全文）

{wiki_block}
"""

    semi_static = f"""
## L1 · AcceptanceContract（≤15 行 · 非 failure_paths 全文）

{contract_table}

## 编排上下文（Main → Sub · 逻辑共享）

- task: `{task.task_path}`
- branch: `{task.git_branch}`
- hat: `{hat}`
- 上一帽摘要: （由 Main 写入 · 非 Sub 互读 KV）
"""

    dynamic_suffix = f"""
## 动态任务指令（唯一高频变化段）

{task.dynamic_query}

【回报硬格式】
Status / Deliverables / Blockers / Judgment（各≤10行）
failure_path_ref 表：| ref | pass/fail | evidence |
"""

    static_chars = len(static_prefix) + len(semi_static)
    dynamic_chars = len(dynamic_suffix)
    return CompiledPrompt(
        static_prefix=static_prefix,
        semi_static=semi_static,
        dynamic_suffix=dynamic_suffix,
        static_char_count=static_chars,
        dynamic_char_count=dynamic_chars,
    )


def print_cache_boundary(compiled: CompiledPrompt) -> None:
    try:
        from rich.console import Console
        from rich.panel import Panel

        console = Console()
        static = compiled.static_prefix + compiled.semi_static
        console.print(Panel(static, title="STATIC+SEMI (cache-friendly)", border_style="blue"))
        console.print(
            Panel(
                compiled.dynamic_suffix,
                title="DYNAMIC (recomputed per hat)",
                border_style="yellow",
            )
        )
        total = compiled.static_char_count + compiled.dynamic_char_count
        ratio = compiled.static_char_count / total * 100 if total else 0
        console.print(
            f"[dim]static≈{compiled.static_char_count} chars · "
            f"dynamic≈{compiled.dynamic_char_count} chars · "
            f"static ratio≈{ratio:.0f}%[/dim]"
        )
    except ImportError:
        print("=" * 50)
        print("STATIC+SEMI:", compiled.static_char_count)
        print(compiled.static_prefix + compiled.semi_static)
        print("=" * 50)
        print("DYNAMIC:", compiled.dynamic_char_count)
        print(compiled.dynamic_suffix)
