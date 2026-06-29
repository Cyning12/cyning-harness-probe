# 方案 · harness-probe Harness 引导 + 技术图谱（v1）

| 项 | 内容 |
| --- | --- |
| **状态** | `planning` |
| **版本** | v1 |
| **日期** | 2026-06-29 |
| **触发** | Phase 1 执行中跳过帽链落盘流程——根因是子项目缺少 Harness 基础框架 |

---

## 1. 根因分析

Phase 1 执行时直接跳过了 00→30→40→50 帽链落盘，事后才回填 task + invoke + review。根因：

| 缺失项 | 影响 |
| --- | --- |
| 无 `CLAUDE.md` | Agent 不知道项目边界和纪律 |
| 无 `.claude/agents/` | 无法 spawn 对照工作区的 harness-* agent |
| 无 `.claude/settings.json` | 无 hook、无权限规则 |
| 无 `docs/_tech_graph/` | Agent 改代码时无结构 Inform，纯靠 prompt 自律 |
| 无 `harness_task_validate.py` | 无 CI 门禁检查 task 字段 |
| `AGENTS.md` 太薄 | 只有读序和边界，缺少完整的 Harness 帽链描述 |

一个正常的 Harness 子项目，Agent 打开后应能在 30 秒内读取完 AGENTS.md + 图谱 → 知道改动边界。harness-probe 目前做不到。

---

## 2. 目标态

```text
harness-probe/
├── CLAUDE.md                          # 薄层入口 → AGENTS.md
├── AGENTS.md                          # 完整帽链纪律 + 读序 + 边界
├── .claude/
│   ├── settings.json                  # hooks + 权限
│   └── agents/
│       └── harness-probe-agent.md     # probe 专用 agent
├── docs/
│   ├── _tech_graph/                   # 技术图谱
│   │   ├── README.md
│   │   ├── 10_cli.ai.md               # CLI 层
│   │   ├── 20_orchestrator.ai.md      # orchestrator 层
│   │   ├── 30_compiler.ai.md          # compiler 层
│   │   ├── 40_builder.ai.md           # builder 层
│   │   ├── 50_graph_loader.ai.md      # graph_loader 层
│   │   ├── 60_models.ai.md            # models 层
│   │   ├── 99_mermaid_protocol.md     # Mermaid 导出协议
│   │   └── graph.json                 # 导出产物
│   ├── harness/                       # Harness 制品
│   │   ├── prompts/                   # 从 @cyning/harness 同步
│   │   ├── tasks/
│   │   │   ├── active/
│   │   │   └── done/
│   │   ├── invokes/
│   │   │   └── by-task/
│   │   └── reviews/
│   └── methodology/                   # 方法论文档（已有）
└── tools/
    └── harness_task_validate.py       # task 门禁脚本
```

---

## 3. 分两步走

### Step A：cyning-harness 引导（1 次操作）

**结论：`npx @cyning/harness init` 可直接用，但需要手动补 AGENTS.md + 图谱。**

`@cyning/harness@2.0.4` 的 `harness-only` profile 提供：

| 轨道 | 是否启用 | 说明 |
| --- | --- | --- |
| `harness_prompts` | ✅ | 复制 10/22/30/40 prompts + invoke 模板到 `docs/harness/prompts/` |
| `ide_cursor` | ✅ | 复制 `.cursor/rules/06-harness-pointer.mdc` |
| `ide_agents` | ❌ | `harness-only` 未启用，需手动创建 `.claude/agents/` |
| `graph` | ❌ | 不复制图谱模板 |
| `ci` | ❌ | 不复制 CI 门禁 |

**需手动补充的：**

| 项 | 方式 | 工作量 |
| --- | --- | --- |
| `CLAUDE.md` | 手动创建（薄指针 → AGENTS.md）| XS |
| `AGENTS.md` 重写 | 基于工作区模板 + probe 专用内容 | S |
| `.claude/agents/harness-probe-agent.md` | 参照工作区 `harness-00-orchestrator.md` 简化 | S |
| `.claude/settings.json` | 参照工作区 baseline | XS |
| `tools/harness_task_validate.py` | 从 IMP-09 结果中定制 | M |
| `.github/workflows/tech-graph.yml` | 新增 CI | S |

**为什么不全用 cyning-harness？**

`@cyning/harness` 是"纪律包"——提供 prompts、模板、读序约定。它不提供：
- 项目专属 CLAUDE.md / AGENTS.md
- 业务技术图谱
- `.claude/` IDE 配置
- 项目专属 CI

所以正确做法是：**`npx @cyning/harness init` 打底 → 手动补 AGENTS 和图谱。**

---

### Step B：技术图谱构建

#### B.1 建模范围

```text
probe 顶层模块
├── CLI (src/probe.py)
│   ├── cmd_compile → subgraph + wiki → build_hat_prompt → persist
│   ├── cmd_verify → validate_task_markdown
│   ├── cmd_run → orchestrator.run_task
│   ├── cmd_watch → load_graph + freeze_id check
│   └── cmd_graph_query → query_subgraph
│
├── orchestrator (src/orchestrator.py)
│   ├── gate_scan → blocks_hat check
│   ├── pre_spawn_verify → contract validation
│   ├── run_task → build_hat_prompt × hats → persist
│   └── _persist_run_graph
│
├── compiler (src/compiler.py)
│   ├── parse_task_markdown → freeze_id / contracts / gates
│   ├── compile_contracts_from_task → AcceptanceContract
│   ├── validate_human_gate_rules
│   ├── parse_human_gates
│   └── retrieve_wiki → Top-K wiki entries
│
├── builder (src/builder.py)
│   ├── build_hat_prompt → hat dispatch
│   ├── _build_static_prefix → freeze_id + mermaid + wiki
│   ├── _build_10_spec_prompt / _build_10_task_prompt / _build_20_review_prompt / _build_50_reinspect_prompt
│   ├── _build_execution_hat_prompt → 30/40
│   └── print_cache_boundary
│
├── graph_loader (src/graph_loader.py)
│   ├── load_graph → graph_v2.json → TechGraph
│   ├── query_subgraph → BFS + Mermaid
│   └── subgraph_to_mermaid
│
└── models (src/models.py)
    ├── GraphNode / GraphEdge / TechGraph
    ├── AcceptanceContract / HumanGate / HarnessTask
    ├── WikiEntry / SubgraphResult / CompiledPrompt
    └── TaskRunNode / TaskRunGraph / BlockedError
```

#### B.2 节点与边

每个 `.ai.md` 文件描述一个模块：

**`10_cli.ai.md`**

```yaml
nodes:
  - id: CLI
    label: "probe CLI"
    kind: entry
    module_id: CLI
    depends_on: [ORCHESTRATOR, GRAPH_LOADER, COMPILER]
    entry_points:
      - "python -m src.probe compile"
      - "python -m src.probe verify"
      - "python -m src.probe run"
      - "python -m src.probe watch"
      - "python -m src.probe graph-query"
```

**`20_orchestrator.ai.md`**

```yaml
nodes:
  - id: ORCHESTRATOR
    label: "HarnessProbeCore"
    kind: service
    module_id: ORCHESTRATOR
    depends_on: [BUILDER, COMPILER, GRAPH_LOADER]
    entry_points:
      - "gate_scan"
      - "pre_spawn_verify"
      - "run_task"
```

依此类推，`30_compiler` → `40_builder` → `50_graph_loader` → `60_models`。

#### B.3 边语义

```yaml
edges:
  - from: CLI
    to: ORCHESTRATOR
    mark: "->"
    type: depends_on
    label: "cmd_run → HarnessProbeCore.run_task"

  - from: CLI
    to: COMPILER
    mark: "->"
    type: depends_on
    label: "cmd_verify → validate_task_markdown"

  - from: ORCHESTRATOR
    to: BUILDER
    mark: "->"
    type: depends_on
    label: "run_task → build_hat_prompt × hats"

  - from: ORCHESTRATOR
    to: COMPILER
    mark: "->"
    type: depends_on
    label: "retrieve_wiki"

  - from: COMPILER
    to: MODELS
    mark: "->"
    type: depends_on

  - from: BUILDER
    to: COMPILER
    mark: "->"
    type: depends_on
    label: "format_contract_table / format_wiki_context"

  - from: GRAPH_LOADER
    to: MODELS
    mark: "->"
    type: depends_on
```

#### B.4 图谱工具链

当前 probe 的 `graph_loader.py` 只读 graph_v2 JSON。有两个选择：

| 方案 | 优点 | 缺点 |
| --- | --- | --- |
| **A. 手写 graph.json** | 无依赖 | 漂移风险 |
| **B. .ai.md → graph_export → graph.json** | 与 Ink 工作区同工具链 | 需引入 `tech_graph_graph_query.py` |

**建议先走方案 A**（手写一份 graph.json，≤30 节点），因为 probe 模块数少且稳定。后续 Phase 2 SDK 重构时再引入正式导出工具链。

---

## 4. CI 门禁（task_validate）

harness-probe 作为 Python 项目，可以引入轻量版 `harness_task_validate.py`：

```yaml
# .github/workflows/tech-graph.yml
name: tech-graph
on:
  pull_request:
  push:
    branches: [main]

jobs:
  task_validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v6
        with:
          python-version: "3.11"
      - name: task validate
        run: |
          FILES=$(git diff --name-only --diff-filter=ACMR origin/main...HEAD -- 'docs/harness/tasks/active/*.md' 'docs/harness/tasks/done/*.md' || true)
          if [ -n "$FILES" ]; then
            for f in $FILES; do
              python tools/harness_task_validate.py "$f"
            done
          fi
```

`tools/harness_task_validate.py`：从 `ai-ink-brain-api-python` 复制定制版，校验 human_gate 表（含 IMP-09 规则）。

---

## 5. 执行顺序

```text
Step 1: npx @cyning/harness init --preset harness-only --ide cursor
        → 复制 prompts / invoke 模板 / .cursor/rules

Step 2: 手动创建 CLAUDE.md + 重写 AGENTS.md
        → 包含完整的 probe 帽链纪律、读序、边界

Step 3: 手动创建 .claude/agents/harness-probe-agent.md
        → 简化版 harness agent

Step 4: 创建 docs/_tech_graph/ 6 个 .ai.md → 手工汇编 graph.json
        → ≤30 节点，覆盖全部 src/ 模块

Step 5: 复制 tools/harness_task_validate.py + .github/workflows/tech-graph.yml
        → CI 门禁

Step 6: 验证：用新 AGENTS.md + 图谱重新执行一个 task
        → 确认 Agent 能走完整帽链落盘
```

---

## 6. 决策点（需人确认）

| 问题 | 建议 | 备选 |
| --- | --- | --- |
| 图谱工具链 | 先手写 graph.json（模块少且稳定） | Phase 2 引入正式导出 |
| `@cyning/harness` profile | `harness-only`（不覆盖业务 task） | 全量 fullstack（会覆盖 coding_wiki 等） |
| task_validate 脚本 | 从 api-python 复制定制版 | 从零写轻量版 |
| `.claude/agents/` 是否需要 spawn | 先单 agent 模式 | Phase 2 引入 spawn |

---

## 7. 预期收益

| 收益 | 指标 |
| --- | --- |
| Agent 改代码前自动读图 | L0 子图裁剪 ≤ depth=2，避免全量理解 |
| 新 task 自动走帽链落盘 | 00→30→40→50 invoke 不遗漏 |
| CI 拦截非法 task | human_gate 缺失 → PR 红 |
| 新维护者 onboarding | AGENTS.md + graph.json ≤30s 读完 |

---

## 修订记录

| 版本 | 日期 | 说明 |
| --- | --- | --- |
| v1 | 2026-06-29 | 初版 · Step A + B 方案 |
