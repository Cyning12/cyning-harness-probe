# Epic · harness-probe Phase 4 · 真执行验证（verify_cmd runner · v0.6）

> **状态**：`approved_for_audit` · HG-TASK-DRAFT approved · HG-AUDIT-R1 pending  
> **task_slug**：`harness-probe-phase4-real-verify-runner-v1`  
> **方案真值**：[`docs/PLAN_PHASE4_v1_zh.md`](../../PLAN_PHASE4_v1_zh.md)  
> **前置**：harness-probe v0.5（`c2d6028` / `v0.5.0`）  
> **目标版本**：v0.6  
> **日期**：2026-06-30

---

## Harness 元信息

| 字段 | 值 |
| --- | --- |
| **track** | `feature` |
| **task_type** | `epic` |
| **module_id** | `RUNNER` / `CLI` / `MCP` |
| **graph_delta** | `none` |
| **test_strategy** | `required` |
| **freeze_id** | `HARNESS-PROBE-PHASE4-v1` |
| **gates_before_code** | `["failure_paths", "freeze_id", "human_gate"]` |
| **orchestration** | Cursor Task 链 |
| **git_branch** | `task/harness-probe-phase4-real-verify-runner-v1` |
| **worktree_root** | `harness-probe/` |

### 人工闸 `human_gate`

| human_gate_id | status | blocks_hats | 说明 |
| --- | --- | --- | --- |
| HG-TASK-DRAFT | **`approved`** | 20-task-audit R1, 30 | 00 起草 · 人签 |
| HG-AUDIT-R1 | **`approved`** | 30 | 20-task-audit R1 通过 · 人签 · 见 [`docs/harness/reviews/REVIEW_task_harness_probe_phase4_real_verify_runner_v1_R1_20260630.md`](../../reviews/REVIEW_task_harness_probe_phase4_real_verify_runner_v1_R1_20260630.md) |

---

## 1. Epic 目标

让 `probe_run` / `probe_audit` 不再只返回 mock pass，而是**真正执行 task 中 AcceptanceContract 的 `verify` 命令**，并支持失败重跑 / 超时处理 / 打回 30 的短回路。

---

## 2. 拆分子任务

| 子任务 | slug | 目标 | 依赖 | 人闸 |
|--------|------|------|------|------|
| **v0.6-a1** | `harness-probe-phase4-a1-sdk-executor-v1` | SDK Executor 基础设施（协议 + SubprocessExecutor + 超时 + 截断 + Runner 接入） | v0.5 | HG-AUDIT-R1 pending |
| **v0.6-a2** | `harness-probe-phase4-a2-cli-mcp-integration-v1` | CLI/MCP 透传 `--executor/--max-retries/--cwd`、重跑逻辑、audit 识别 blocked、发布 v0.6 | v0.6-a1 | HG-AUDIT-R1 pending |

**执行顺序：串行。** v0.6-a2 必须等 v0.6-a1 合并到 main 后才能开工，避免并行改同一模块（`harness_sdk/runner.py`）。

---

## 3. 关键人类验收节点

| 节点 | 触发条件 | 验收人 | 验收内容 |
|------|----------|--------|----------|
| **R1 · task 书面审** | 本 Epic + 子 task 起草完成 | 维护者 | 审查 task 范围、失败路径、验收标准、人闸表 |
| **R2 · a1 代码审** | v0.6-a1 30 执行完成、40 自检通过 | 维护者 | `test_sdk_executor.py` 覆盖完整；`runner.py` 无副作用破坏 |
| **R3 · a1 合并前** | PR 到 main | CI + 维护者 | `pytest tests/ -q` 全绿 |
| **R4 · a2 代码审** | v0.6-a2 30 执行完成、40 自检通过 | 维护者 | CLI/MCP 参数透传正确；默认仍 mock |
| **R5 · v0.6 发布** | a2 合并后 | 维护者 | 打 tag `v0.6.0`、push、验证远程 |

---

## 3.1 失败路径（Epic 级）

| # | Scenario ID | 触发条件 | 系统行为 | 可重试 | 用户可见 |
| --- | --- | --- | --- | --- | --- |
| F1 | `fp-epic-scope-creep` | 子任务边界不清，a2 提前改 runner | 00 拒开工，要求先完成 a1 | 否 | BLOCKED |
| F2 | `fp-audit-miss` | R1 未通过就进入 30 | 30 拒改码 | 否 | 以 task 表为准 |

## 3.2 验收标准（Epic 级）

- [ ] v0.6-a1 合并后 `pytest tests/ -q` 全绿
- [ ] v0.6-a2 合并后 `pytest tests/ -q` 全绿
- [ ] v0.6-a2 发布后 remote tag `v0.6.0` 存在

---

## 4. 范围 / 非范围（Epic 级）

### 范围

- SDK Executor 抽象与 SubprocessExecutor 实现
- Runner 支持 mock / real 执行切换
- CLI / MCP 参数透传
- 超时、输出截断、失败重跑
- `probe_audit` 识别 blocked 并建议打回 30

### 非范围

- 不接入 LLM 自动修复（归 v0.8）
- 不引入 sandbox 隔离（归 v0.8）
- 不改帽链语义
- 不改业务 graph.json
- 不默认开启真实执行

---

## 5. 子任务链接

- [v0.6-a1 SDK Executor](./task_harness_probe_phase4_a1_sdk_executor_v1.md)
- [v0.6-a2 CLI/MCP 集成 + 发布](./task_harness_probe_phase4_a2_cli_mcp_integration_v1.md)

---

## 6. 修订记录

| 版本 | 日期 | 说明 |
| --- | --- | --- |
| v1 | 2026-06-30 | 00 起草 · 拆分为 v0.6-a1 + v0.6-a2 |
| v1.1 | 2026-06-30 | HG-TASK-DRAFT approved，进入 20-task-audit R1 |
