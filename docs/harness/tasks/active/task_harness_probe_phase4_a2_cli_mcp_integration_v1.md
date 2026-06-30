# Task · harness-probe v0.6-a2 · CLI/MCP 集成与发布

> **状态**：`draft` · 待 v0.6-a1 完成后进入 20-task-audit  
> **task_slug**：`harness-probe-phase4-a2-cli-mcp-integration-v1`  
> **父 Epic**：[`docs/harness/tasks/active/task_harness_probe_phase4_real_verify_runner_v1.md`](./task_harness_probe_phase4_real_verify_runner_v1.md)  
> **方案真值**：[`docs/PLAN_PHASE4_v1_zh.md`](../../PLAN_PHASE4_v1_zh.md)  
> **前置**：v0.6-a1 SDK Executor 已合并  
> **目标版本**：v0.6  
> **日期**：2026-06-30

---

## Harness 元信息

| 字段 | 值 |
| --- | --- |
| **track** | `feature` |
| **lightweight_task** | `no` |
| **module_id** | `CLI` / `MCP` |
| **graph_delta** | `none` |
| **test_strategy** | `required` |
| **freeze_id** | `HARNESS-PROBE-PHASE4-v1` |
| **gates_before_code** | `["failure_paths", "freeze_id", "human_gate"]` |
| **orchestration** | Cursor Task 链 |
| **git_branch** | `task/harness-probe-phase4-a2-cli-mcp-integration-v1` |
| **worktree_root** | `harness-probe/` |

### 人工闸 `human_gate`

| human_gate_id | status | blocks_hats | 说明 |
| --- | --- | --- | --- |
| HG-TASK-DRAFT | `pending` | 20-task-audit R1, 30 | 待 00 签 |
| HG-AUDIT-R1 | `pending` | 30 | 20-task-audit R1 通过 · 人签 |

---

## 1. 背景与目标

在 v0.6-a1 SDK Executor 完成后，v0.6-a2 负责把真实执行能力透传到 CLI 与 MCP，并支持失败重跑、审计识别 blocked、最终发布 v0.6。

---

## 2. 范围

### 必须交付

| ID | 交付物 | 位置 | 验收 |
| --- | --- | --- | --- |
| D1 | CLI `--executor` / `--max-retries` / `--cwd` | `harness_probe/cli.py` | 默认 mock，显式 real 才真跑 |
| D2 | 重跑逻辑 | `harness_sdk/runner.py` | `max_retries` 失败时重跑 N 次 |
| D3 | MCP `probe_run` 扩展 | `harness_mcp/tools.py` | `executor` / `max_retries` / `cwd` |
| D4 | `probe_audit` 识别 blocked | `harness_mcp/tools.py` | blocked 节点输出 `next_hat: "30"` |
| D5 | 文档更新 | `README.md` / `CHANGELOG.md` | v0.6 说明 |
| D6 | 版本 bump | `pyproject.toml` / `harness_probe/__init__.py` | version = 0.6.0 |
| D7 | 端到端测试 | `tests/test_cli.py` / `tests/test_mcp_tools.py` | 覆盖 `--executor real` / 重跑 |

### 明确不做

- 不接入 LLM 自动修复
- 不引入 sandbox 隔离
- 不改帽链语义

---

## 3. 失败路径

| # | Scenario ID | 触发条件 | 系统行为 | 可重试 | 用户可见 |
| --- | --- | --- | --- | --- | --- |
| F1 | `fp-real-not-authorized` | 未显式 `--executor real` | 拒绝运行 | 否 | 提示显式授权 |
| F2 | `fp-retry-exhausted` | 重跑 N 次仍失败 | run_node.status = blocked | 否 | audit 建议打回 30 |
| F3 | `fp-cwd-not-found` | `--cwd` 目录不存在 | 报错 | 否 | BLOCKED |

---

## 4. 验收标准

- [ ] `python -m harness_probe.cli run --executor real --from-hat 30 --to-hat 40` 真实执行
- [ ] `--max-retries 2` 失败时重跑 2 次
- [ ] 重跑耗尽后节点 blocked，audit 建议 next_hat=30
- [ ] MCP `probe_run` 支持 `executor="real"`、`max_retries=2`
- [ ] `pytest tests/ -q` 全绿
- [ ] 发布 tag `v0.6.0` 并 push

---

## 5. 依赖

- v0.6-a1 SDK Executor 已合并到 main（commit 待定）

---

## 6. 修订记录

| 版本 | 日期 | 说明 |
| --- | --- | --- |
| v1 | 2026-06-30 | 00 起草 · v0.6-a2 CLI/MCP 集成 |
