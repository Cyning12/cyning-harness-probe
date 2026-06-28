# Harness Probe · 架构（v1）

## 1. 定位

**Harness Probe** 不是 ChatBot，而是 **任务派遣与验收引擎** 的最小可运行探针：

- **L0**：`graph_v2` 子图查询（结构 Inform）
- **L1**：`failure_paths` → **AcceptanceContract**（过程轨）
- **L1.5**：`TaskRunGraph` 运行时实例（会话资产）
- **L2**：Wiki 摘要 stub（冷记忆）

**明确不做**：LLM Runtime（retry / token cap / step 上限）——归 Kimi/Claude Host。

---

## 2. 模块

```text
src/graph_loader.py   # load_graph · query_subgraph (BFS)
src/compiler.py       # parse task · compile contracts · wiki retrieve
src/builder.py        # 三段式 Prompt · cache 边界可视化
src/orchestrator.py   # HarnessProbeCore · gate_scan · dry-run 帽循环
src/probe.py          # CLI
```

---

## 3. Prompt 三段式（KV-Cache 友好）

```text
[STATIC]   System + L0 mermaid 子图 + L2 摘要
[SEMI]     L1 contract 表 + 编排元数据
[DYNAMIC]  当前 hat 指令 + 上一帽一行摘要
```

目标：动态段占比尽量小（Probe 终端会打印 static ratio）。

---

## 4. 双图谱

| 层 | 文件 | 生命周期 |
| --- | --- | --- |
| L0 | `data/graph/*.json` 或 `--graph ../ai-ink-brain-api-python/...` | 仓库级 |
| L1.5 | `outputs/task_run_*.json` | 会话级 |

---

## 5. 路线图

| 阶段 | Probe v0.1 | 未来 Core |
| --- | --- | --- |
| L0 | 本地 JSON + BFS | Git pull + freeze_id watch |
| L1 | Markdown 表格解析 | LLM 辅助 + manifest 对齐 |
| L2 | JSON stub | 向量 retrieve |
| Subagent | dry-run mock | LLM + sandbox bash |
| 验证 | mock pass | 真跑 verify_cmd + fix-verify |
| 进化 | 文本 PR 提案 | 审计 Agent + 22 gate |

---

## 6. 与工作区 Harness 对齐

| 工作区真值 | Probe 对应 |
| --- | --- |
| `PROMPT_cursor_task_chain_serial_v1.md` §4.5 / §5.3 / §5.4 | `pre_spawn_verify` · contract · evidence 表 |
| `COMPARISON…` §2.2 | 不分域写 guardrails 进业务 YAML |
| `graph_query` 闸口 B | `graph-query` CLI |

---

## 修订记录

| 日期 | 说明 |
| --- | --- |
| 2026-06-27 | v1 初版 |
