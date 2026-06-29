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

**结论：`npx @cyning/harness init --preset harness-only` 打底，AGENTS/CLAUDE 片段从 `ide/adapters/` 取。**

`@cyning/harness@2.0.4` 的 `harness-only` profile 提供：

| 轨道 | 启用 | 说明 |
| --- |:---:| --- |
| `harness_prompts` | ✅ | 复制 10/22/30/40 prompts + TEMPLATE 到 `docs/harness/prompts/` |
| `harness_invoke_template` | ✅ | invoke 快照模板 |
| `ide_cursor` | ✅ | 复制 `.cursor/rules/06-harness-pointer.mdc` |

**不需要 `fullstack-node-py` profile**——probe 无业务代码，Wiki、standards L1/L2、task bootstrap 都是冗余。

**AGENTS.md / CLAUDE.md 已有模板**：

`cyning-harness/ide/adapters/` 下有：

- `CLAUDE.md.fragment.example` → Harness Starter 薄层（Claude Code 用）
- `AGENTS.md.fragment.example` → Harness Starter 通用 Agent 入口

这两个片段覆盖了：task 执行前纪律（读 task、GATE_VERIFY、HG-AUDIT-R1 拒改码）、合并前验证、invoke 路径、关键词和 POINTER。probe 只需在 AGENTS 片段基础上追加 **专属读序 + 命令 + 边界**（约 20 行）。

**需手动补充的（不能从 cyning-harness 拿到的）：**

| 项 | 方式 | 工作量 |
| --- | --- | --- |
| AGENTS.md probe 专属段 | 在片段下方追加读序、命令、边界 | XS |
| `.claude/agents/harness-probe-agent.md` | 参照工作区 `harness-00-orchestrator.md` 简化 | S |
| `.claude/settings.json` | 参照工作区 baseline | XS |
| `docs/_tech_graph/` + `graph.json` | 手写 6 个 `.ai.md` → 手写 graph.json | M |
| `tools/harness_task_validate.py` | 从 `ai-ink-brain-api-python` 复制定制版 | S |
| `.github/workflows/tech-graph.yml` | 新增 task_validate job | S |

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

## 5. 执行顺序（修正版）

```text
Step 1: npx @cyning/harness init --preset harness-only --ide cursor
        → 复制 prompts / invoke 模板 / .cursor/rules

Step 2: 从 cyning-harness/ide/adapters/ 取 AGENTS.md.fragment.example + CLAUDE.md.fragment.example
        → AGENTS 片段末尾追加 probe 专属段（读序、命令、边界，~20 行）
        → CLAUDE 片段直接用作 CLAUDE.md（薄层 POINTER）

Step 3: 手动创建 .claude/agents/harness-probe-agent.md
        → 简化版 harness agent（YAML frontmatter + 必读指向）

Step 4: 创建 docs/_tech_graph/ 6 个 .ai.md → 手工汇编 graph.json
        → ≤30 节点，覆盖全部 src/ 模块

Step 5: 复制 tools/harness_task_validate.py + .github/workflows/tech-graph.yml
        → CI 门禁含 IMP-09 human_gate 校验

Step 6: 验证：用新 AGENTS + 图谱重新执行一个 task
        → 确认 Agent 能走完整 00→30→40→50 帽链落盘
```

---

## 6. 决策点（需人确认）

| 问题 | 建议 | 理由 |
| --- | --- | --- |
| `@cyning/harness` profile | `harness-only` | fullstack 带 Wiki + standards L1/L2 + task bootstrap，probe 不需要 |
| AGENTS.md 来源 | `ide/adapters/AGENTS.md.fragment.example` + 追加 probe 段 | 片段已覆盖 Harness 纪律 80%，只需补 ~20 行专属内容 |
| CLAUDE.md 来源 | `ide/adapters/CLAUDE.md.fragment.example` 直接使用 | 薄层 POINTER，probe 无需改写 |
| 图谱工具链 | 先手写 graph.json（≤30 节点） | 模块少且稳定，Phase 2 引入正式导出 |
| task_validate 脚本 | 从 `ai-ink-brain-api-python` 复制定制版 | 含 IMP-09 human_gate 校验 |
| `.claude/agents/` | 先单 agent 模式 | probe 改动范围小，不需要 spawn 多 agent |

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
