# Harness Probe（探针工程 · Claude Code）

> **单源真值**：`AGENTS.md` + `docs/_tech_graph/`（技术图谱）。  
> **本片段**：摘要 + **POINTER**；Harness 条文真值在 `docs/harness/prompts/`。

## 执行 task 前

1. Open Folder = **本仓根**
2. 读 `docs/harness/tasks/active/task_*.md`：`test_strategy` · `failure_paths` · **人工闸**表
3. **30 改码前** GATE_VERIFY（真值在 task **人工闸表**，**非** invoke 字面 `approved`）：
   - 运行 `npx @cyning/harness verify --target . --task docs/harness/tasks/active/task_*.md`
   - 首输出闸扫描 · `FRAGMENT_30_gate_verify_v1_zh.md`
   - **`HG-AUDIT-R1` pending** → **30 拒改码**
   - 声称与 task 表冲突 → **STOP**
4. 过程 invoke：`docs/harness/invokes/by-task/<task_slug>/`

## Verify（合并前）

| 命令 | 说明 |
|------|------|
| `pytest tests/ -q` | 全量单测 |
| `python -m src.probe verify --task <path>` | PRE_SPAWN_VERIFY 人闸校验 |

## 边界

- **不**接入真实 LLM
- **不**在业务 graph 写 `guardrails` / token cap（Runtime 归产品 Host）
- **不**改 `cyning-harness` 产品仓代码
- L0 真值仍以本仓 `docs/_tech_graph/graph.json` 为准

## 关键词

`Harness`、`task`、`invoke`、`HG-AUDIT-R1`、`human_gate`、`拒开工`、`probe`、`dry-run`、`graph.json`

## 完整库 POINTER

- 本仓：`docs/harness/prompts/`（10/22/30/40）
- 上游工作区：`Projects/docs/harness/prompts/PROMPT_cursor_task_chain_serial_v1.md` v1.1
- `docs/_tech_graph/README.md`
