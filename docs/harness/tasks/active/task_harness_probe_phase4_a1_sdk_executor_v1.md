# Task · harness-probe v0.6-a1 · SDK Executor 基础设施

> **状态**：`draft` · 待 20-task-audit R1  
> **task_slug**：`harness-probe-phase4-a1-sdk-executor-v1`  
> **父 Epic**：[`docs/harness/tasks/active/task_harness_probe_phase4_real_verify_runner_v1.md`](./task_harness_probe_phase4_real_verify_runner_v1.md)  
> **方案真值**：[`docs/PLAN_PHASE4_v1_zh.md`](../../PLAN_PHASE4_v1_zh.md)  
> **前置**：harness-probe v0.5（`c2d6028` / `v0.5.0`）  
> **目标版本**：v0.6-a1  
> **日期**：2026-06-30

---

## Harness 元信息

| 字段 | 值 |
| --- | --- |
| **track** | `feature` |
| **lightweight_task** | `no` |
| **module_id** | `RUNNER` / `EXECUTOR` |
| **graph_delta** | `none` |
| **test_strategy** | `required` |
| **freeze_id** | `HARNESS-PROBE-PHASE4-v1` |
| **gates_before_code** | `["failure_paths", "freeze_id", "human_gate"]` |
| **orchestration** | Cursor Task 链 |
| **git_branch** | `task/harness-probe-phase4-a1-sdk-executor-v1` |
| **worktree_root** | `harness-probe/` |

### 人工闸 `human_gate`

| human_gate_id | status | blocks_hats | 说明 |
| --- | --- | --- | --- |
| HG-TASK-DRAFT | `approved` | 20-task-audit R1, 30 | 00 起草 · 人签 |
| HG-AUDIT-R1 | **`approved`** | 30 | 20-task-audit R1 通过 · 人签 · 见 [`docs/harness/reviews/REVIEW_task_harness_probe_phase4_real_verify_runner_v1_R1_20260630.md`](../../reviews/REVIEW_task_harness_probe_phase4_real_verify_runner_v1_R1_20260630.md) |

---

## 1. 背景与目标

作为 Phase 4 Epic 的第一阶段，v0.6-a1 专注在 SDK 层建立**可插拔的 verify 执行器**，使 `TaskRunner` 能选择 mock 或真实 subprocess 执行，并支持超时控制。本阶段不改动 CLI / MCP，仅改 `harness_sdk/`。

---

## 2. 范围

### 必须交付

| ID | 交付物 | 位置 | 验收 |
| --- | --- | --- | --- |
| D1 | `VerifyExecutor` Protocol | `harness_sdk/executor.py` | 异步 `run(cmd, cwd) -> ExecutionResult` |
| D2 | `SubprocessExecutor` | `harness_sdk/executor.py` | 用 `asyncio.create_subprocess_shell` 执行命令 |
| D3 | `ExecutionResult` 模型 | `harness_sdk/models.py` | returncode / stdout / stderr / elapsed_ms |
| D4 | Runner 接入 executor | `harness_sdk/runner.py` | `__init__` 接收 executor；`_execute_hat` 按 executor 分发 |
| D5 | 超时控制 | `harness_sdk/executor.py` | 默认 60s 超时，可配置 |
| D6 | 输出截断 | `harness_sdk/executor.py` | stdout > 4K 时截断并加标记 |
| D7 | 测试 | `tests/test_sdk_executor.py` | mock / real / timeout / output-truncated |

### 明确不做

- 不重试逻辑（归 v0.6-a2）
- 不改 CLI / MCP
- 不接入 LLM / sandbox

---

## 3. 失败路径

| # | Scenario ID | 触发条件 | 系统行为 | 可重试 | 用户可见 |
| --- | --- | --- | --- | --- | --- |
| F1 | `fp-verify-not-found` | 命令不存在 | returncode ≠ 0 | 否 | evidence = stderr |
| F2 | `fp-verify-timeout` | 超时 | TimeoutError | 否 | evidence = "[timeout]" |
| F3 | `fp-verify-truncated` | 输出 > 4K | 截断 | 是 | evidence 含 `[truncated]` |

---

## 4. 验收标准

- [ ] `SubprocessExecutor.run("echo ok")` 返回 returncode=0
- [ ] `SubprocessExecutor.run("exit 1")` 返回 returncode=1
- [ ] 超时命令抛出 TimeoutError 或被包装为 blocked
- [ ] 输出 > 4K 时被截断
- [ ] `TaskRunner(executor=None)` 保持 mock 行为
- [ ] `TaskRunner(executor=SubprocessExecutor())` 真实执行 contract.verify
- [ ] `pytest tests/test_sdk_executor.py -q` 全绿
- [ ] `pytest tests/ -q` 全绿（≥ 36 个基线）

---

## 5. 依赖

- harness-probe v0.5（`c2d6028` / `v0.5.0`）

---

## 6. 修订记录

| 版本 | 日期 | 说明 |
| --- | --- | --- |
| v1 | 2026-06-30 | 00 起草 · v0.6-a1 SDK Executor |
