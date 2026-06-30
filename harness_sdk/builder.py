"""KV-Cache 友好的 Prompt 三段式组装 · 支持全帽链"""

from __future__ import annotations

from harness_sdk.compiler import format_contract_table, format_wiki_context
from harness_sdk.models import CompiledPrompt, HarnessTask, SubgraphResult, TechGraph, WikiEntry


def build_hat_prompt(
    hat: str,
    graph: TechGraph,
    task: HarnessTask,
    subgraph: SubgraphResult,
    wiki_entries: list[WikiEntry],
    handoff_summary: str = "",
) -> CompiledPrompt:
    """按帽子生成三段式 Prompt。

    Args:
        hat: 帽子编号，如 "10-spec", "10-task", "20-review", "30", "40", "50-reinspect"
        graph: 完整图谱
        task: 解析后的 task 对象
        subgraph: 已裁剪子图
        wiki_entries: L2 摘要列表
        handoff_summary: 上一帽摘要
    """
    if hat in {"30", "40"}:
        return _build_execution_hat_prompt(hat, graph, task, subgraph, wiki_entries, handoff_summary)
    if hat == "10-spec":
        return _build_10_spec_prompt(graph, task, subgraph, wiki_entries, handoff_summary)
    if hat == "10-task":
        return _build_10_task_prompt(graph, task, subgraph, wiki_entries, handoff_summary)
    if hat == "20-review":
        return _build_20_review_prompt(graph, task, subgraph, wiki_entries, handoff_summary)
    if hat in {"50-reinspect", "50"}:
        return _build_50_reinspect_prompt(graph, task, subgraph, wiki_entries, handoff_summary)
    raise ValueError(f"Unsupported hat: {hat}")


def build_subagent_prompt(
    graph: TechGraph,
    task: HarnessTask,
    hat: str,
    subgraph: SubgraphResult,
    wiki_entries: list[WikiEntry],
) -> CompiledPrompt:
    """兼容旧接口：默认按 hat 生成 Prompt（无上一帽摘要）。"""
    return build_hat_prompt(hat, graph, task, subgraph, wiki_entries, handoff_summary="（首轮无上一帽）")


def _build_static_prefix(
    freeze: str,
    subgraph: SubgraphResult,
    wiki_block: str,
) -> str:
    return f"""# [HARNESS PROBE] System · freeze_id: {freeze}

## L0 · 业务拓扑（局部子图 · depth={subgraph.depth} · entry={subgraph.entry_node})

```mermaid
{subgraph.mermaid}
```

节点 id 列表：{", ".join(subgraph.node_ids)}

## L2 · 冷记忆摘要（合成 · 非 invoke 全文）

{wiki_block}
"""


def _build_10_spec_prompt(
    graph: TechGraph,
    task: HarnessTask,
    subgraph: SubgraphResult,
    wiki_entries: list[WikiEntry],
    handoff_summary: str,
) -> CompiledPrompt:
    freeze = task.freeze_id or graph.freeze_id
    wiki_block = format_wiki_context(wiki_entries)
    static_prefix = _build_static_prefix(freeze, subgraph, wiki_block)

    semi_static = f"""
## L1 · 需求上下文（从 task 提取）

- task: `{task.task_path}`
- branch: `{task.git_branch}`
- hat: `10-spec`
- 上一帽摘要: {handoff_summary}

> 本帽输入为 task 的 **背景、范围、非范围、验收标准、失败路径**。不要写实现代码，只输出 SPEC 草案。
"""

    dynamic_suffix = f"""
## 动态任务指令（唯一高频变化段）

{task.dynamic_query}

你正在扮演 **10-spec 需求分析帽**。严格遵循工作区 `PROMPT_00_draft_spec_or_task_v1_zh.md`：
1. 通读 task 背景、范围、非范围、失败路径、验收标准。
2. 输出 SPEC 草案，至少包含：
   - §1 背景与目标
   - §2 范围 / 非范围
   - §3 行为变更（Delta · ADDED/MODIFIED/REMOVED）
   - §4 验收标准（可验证）
   - §5 失败路径（F1/F2/F3…）
   - §6 思考轮（R0–R5）
3. 默认进行 R0–R5 五轮思考轮；每轮只推进分析，不直接写代码。
4. 若信息不足，列出追问清单（≤5 条），不要臆测填充。

【禁止】
- 在业务 *.graph.yaml 新增 guardrails / token cap / max_retries 字段
- 直接写实现代码或具体函数签名

【回报硬格式】
Status / Deliverables / Blockers / Judgment（各≤10行）
"""

    return CompiledPrompt(
        static_prefix=static_prefix,
        semi_static=semi_static,
        dynamic_suffix=dynamic_suffix,
        static_char_count=len(static_prefix) + len(semi_static),
        dynamic_char_count=len(dynamic_suffix),
    )


def _build_execution_hat_prompt(
    hat: str,
    graph: TechGraph,
    task: HarnessTask,
    subgraph: SubgraphResult,
    wiki_entries: list[WikiEntry],
    handoff_summary: str,
) -> CompiledPrompt:
    freeze = task.freeze_id or graph.freeze_id
    wiki_block = format_wiki_context(wiki_entries)
    contract_table = format_contract_table(task.contracts)
    static_prefix = _build_static_prefix(freeze, subgraph, wiki_block)

    semi_static = f"""
## L1 · AcceptanceContract（≤15 行 · 非 failure_paths 全文）

{contract_table}

## 编排上下文（Main → Sub · 逻辑共享）

- task: `{task.task_path}`
- branch: `{task.git_branch}`
- hat: `{hat}`
- 上一帽摘要: {handoff_summary}
"""

    dynamic_suffix = f"""
## 动态任务指令（唯一高频变化段）

{task.dynamic_query}

【禁止】
- 在业务 *.graph.yaml 新增 guardrails / token cap / max_retries 字段（Runtime 归产品 Host）
- 将 failure_paths 全文粘贴进本 Prompt；只以上方 AcceptanceContract 表为准

【回报硬格式】
Status / Deliverables / Blockers / Judgment（各≤10行）

【failure_path_ref 收工表】（30 / 40 帽必填）
| ref | pass/fail | evidence |
| --- | --- | --- |
| F1 | pass | 命令/文件:行 |
"""

    return CompiledPrompt(
        static_prefix=static_prefix,
        semi_static=semi_static,
        dynamic_suffix=dynamic_suffix,
        static_char_count=len(static_prefix) + len(semi_static),
        dynamic_char_count=len(dynamic_suffix),
    )


def _build_10_task_prompt(
    graph: TechGraph,
    task: HarnessTask,
    subgraph: SubgraphResult,
    wiki_entries: list[WikiEntry],
    handoff_summary: str,
) -> CompiledPrompt:
    freeze = task.freeze_id or graph.freeze_id
    wiki_block = format_wiki_context(wiki_entries)
    static_prefix = _build_static_prefix(freeze, subgraph, wiki_block)

    spec_section = ""
    if task.spec_text:
        spec_section = f"""
## L1 · 关联 SPEC（已 approved）

来源：{task.spec_path}

{task.spec_text[:2000]}

> 若 SPEC 与本 task 目标冲突，以本 task 目标为准，并在 Blockers 中说明。
"""
    elif task.spec_path:
        spec_section = f"""
## L1 · 关联 SPEC

来源：{task.spec_path}
> SPEC 文件未成功加载，请基于 task 背景直接起草。
"""

    semi_static = f"""
## L1 · task 起草上下文

- task: `{task.task_path}`
- branch: `{task.git_branch}`
- hat: `10-task`
- 上一帽摘要: {handoff_summary}
{spec_section}

> 本帽输出为完整 `task.md` 骨架（Harness 元信息、范围、失败路径、验收标准）。不要写实现代码。
"""

    dynamic_suffix = f"""
## 动态任务指令（唯一高频变化段）

{task.dynamic_query}

你正在扮演 **10-task 需求分析帽**。输入为已 approved SPEC（若提供）+ 本 task 目标：
1. 填充 task §5 思考轮（R0–R5）。
2. 从 SPEC 失败路径/验收标准映射出本 task 的 failure_paths 表（≥1 行 F1）。
3. 输出完整 task.md 骨架，必须含：
   - Harness 元信息表（test_strategy、git_branch、freeze_id）
   - 范围 / 非范围
   - 行为变更（Delta）
   - 失败路径（F1/F2/F3…）
   - 验收标准（含字面 `pytest` 若 test_strategy=required）
4. 不要写实现代码。

【禁止】
- 在业务 *.graph.yaml 新增 guardrails / token cap / max_retries 字段
- 直接写实现代码或具体函数签名

【回报硬格式】
Status / Deliverables / Blockers / Judgment（各≤10行）
"""

    return CompiledPrompt(
        static_prefix=static_prefix,
        semi_static=semi_static,
        dynamic_suffix=dynamic_suffix,
        static_char_count=len(static_prefix) + len(semi_static),
        dynamic_char_count=len(dynamic_suffix),
    )


def _build_20_review_prompt(
    graph: TechGraph,
    task: HarnessTask,
    subgraph: SubgraphResult,
    wiki_entries: list[WikiEntry],
    handoff_summary: str,
) -> CompiledPrompt:
    freeze = task.freeze_id or graph.freeze_id
    wiki_block = format_wiki_context(wiki_entries)
    static_prefix = _build_static_prefix(freeze, subgraph, wiki_block)
    target = task.review_target or "task"

    semi_static = f"""
## L1 · 审核上下文

- 审核对象：`{target}`
- 来源文件：`{task.task_path}`
- branch: `{task.git_branch}`
- hat: `20-review`
- 上一帽摘要: {handoff_summary}

> 本帽为 **20-{target}-audit**。重点检查：failure_paths 可操作性、验收标准可验证、范围无隐含扩大、非范围明确。
"""

    dynamic_suffix = f"""
## 动态任务指令（唯一高频变化段）

{task.dynamic_query}

你正在扮演 **20-review 审核帽（{target} 审核）**。
1. 通读输入 `{target}` 全文，重点检查：
   - failure_paths 表至少 1 行且触发条件/预期行为明确
   - 验收标准可执行（test_strategy=required 时须含 `pytest`）
   - 范围 / 非范围无隐含扩大
   - human_gate 表与 blocks_hats 一致
2. 若通过 → 输出 **"签收 / 关闭"**， human_gate HG-AUDIT-R1 视为 approved。
3. 若阻塞 → 输出 **"打回至 10-{target}"**，列出具体缺口项（≤5 条）。
4. 生成"下一棒可复制 Prompt"片段。

【禁止】
- 代签 human_gate；只输出审核结论，不写 approved 到源文件
- 直接修改被审文档内容

【回报硬格式】
Status: approved / blocked
Deliverables: 审核意见摘要
Blockers: 若 blocked，逐条列出
Judgment: 下一棒建议
"""

    return CompiledPrompt(
        static_prefix=static_prefix,
        semi_static=semi_static,
        dynamic_suffix=dynamic_suffix,
        static_char_count=len(static_prefix) + len(semi_static),
        dynamic_char_count=len(dynamic_suffix),
    )


def _build_50_reinspect_prompt(
    graph: TechGraph,
    task: HarnessTask,
    subgraph: SubgraphResult,
    wiki_entries: list[WikiEntry],
    handoff_summary: str,
) -> CompiledPrompt:
    freeze = task.freeze_id or graph.freeze_id
    wiki_block = format_wiki_context(wiki_entries)
    contract_table = format_contract_table(task.contracts)
    static_prefix = _build_static_prefix(freeze, subgraph, wiki_block)

    run_summary = ""
    if task.run_output_path:
        run_summary = f"\n- 关联运行记录：`{task.run_output_path}`\n- 验收时须对照其中 failure_path_ref 表。"

    semi_static = f"""
## L1 · AcceptanceContract 与运行记录

{contract_table}
{run_summary}

## 编排上下文（Main → Sub · 逻辑共享）

- task: `{task.task_path}`
- branch: `{task.git_branch}`
- hat: `50-reinspect`
- 上一帽摘要: {handoff_summary}
"""

    mode_note = (
        "global 模式额外检查：freeze_id 一致、human_gate 全 approved、graph_delta 已落盘。"
        if task.reinspect_mode == "global"
        else "独立复检模式：只核验收证据，不重复跑测试。"
    )

    dynamic_suffix = f"""
## 动态任务指令（唯一高频变化段）

{task.dynamic_query}

你正在扮演 **50-reinspect {task.reinspect_mode} 复检帽**。
1. 读取 task 全文 + 关联 task_run JSON（若提供）。
2. 核对每个 failure_path_ref 是否有 evidence（命令/文件:行）。
3. 若全部 pass → 输出 **"CLOSE"**，更新 task 状态为 done。
4. 若有 fail → 输出打回目标（30 / 40 / 10-task / 10-spec），不进入合并。
5. {mode_note}

【回报硬格式】
Status / Deliverables / Blockers / Judgment
- 验收表：| ref | pass/fail | evidence |
- 合并建议：若通过，输出 merge 建议；若失败，输出 next_hat
"""

    return CompiledPrompt(
        static_prefix=static_prefix,
        semi_static=semi_static,
        dynamic_suffix=dynamic_suffix,
        static_char_count=len(static_prefix) + len(semi_static),
        dynamic_char_count=len(dynamic_suffix),
    )
