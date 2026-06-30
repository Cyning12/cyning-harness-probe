# Invoke · 20-task-audit R1 · harness-probe Phase 4 真执行验证

| 项 | 内容 |
| --- | --- |
| **task** | `docs/harness/tasks/active/task_harness_probe_phase4_real_verify_runner_v1.md` |
| **task_slug** | `harness-probe-phase4-real-verify-runner-v1` |
| **hat** | `20-task-audit` |
| **human_gate** | HG-TASK-DRAFT `approved` · HG-AUDIT-R1 `pending` |
| **freeze_id** | `HARNESS-PROBE-PHASE4-v1` |
| **日期** | 2026-06-30 |

## 审核对象

1. Epic：[`docs/harness/tasks/active/task_harness_probe_phase4_real_verify_runner_v1.md`](../../tasks/active/task_harness_probe_phase4_real_verify_runner_v1.md)
2. 子任务 v0.6-a1：[`docs/harness/tasks/active/task_harness_probe_phase4_a1_sdk_executor_v1.md`](../../tasks/active/task_harness_probe_phase4_a1_sdk_executor_v1.md)
3. 子任务 v0.6-a2：[`docs/harness/tasks/active/task_harness_probe_phase4_a2_cli_mcp_integration_v1.md`](../../tasks/active/task_harness_probe_phase4_a2_cli_mcp_integration_v1.md)
4. 方案：[`docs/PLAN_PHASE4_v1_zh.md`](../../PLAN_PHASE4_v1_zh.md)

## 20-task-audit Prompt

```text
你正在扮演 harness-probe 20-task-audit 审核帽。

审核对象：
- Epic: docs/harness/tasks/active/task_harness_probe_phase4_real_verify_runner_v1.md
- v0.6-a1: docs/harness/tasks/active/task_harness_probe_phase4_a1_sdk_executor_v1.md
- v0.6-a2: docs/harness/tasks/active/task_harness_probe_phase4_a2_cli_mcp_integration_v1.md
- 方案: docs/PLAN_PHASE4_v1_zh.md

重点检查：
1. Epic 拆分是否合理？v0.6-a1 与 v0.6-a2 的边界是否清晰？串行依赖是否正确？
2. 每个 task 的 failure_paths 是否覆盖主要风险（命令不存在、超时、输出截断、重跑耗尽、未授权真实执行）？
3. 验收标准是否可执行？test_strategy=required 是否有对应的测试文件计划？
4. 范围 / 非范围是否无隐含扩大？是否明确不碰 LLM / sandbox / 帽链语义 / graph.json？
5. human_gate 表与 blocks_hats 是否一致？HG-AUDIT-R1 是否正确阻塞 30？
6. 关键人类验收节点（R1–R5）是否完整、合理？

若通过 → 输出 "签收 / 关闭"，并说明 HG-AUDIT-R1 视为 approved。
若阻塞 → 输出 "打回至 00"，列出具体缺口项（≤5 条）。

【回报硬格式】
Status: approved / blocked
Deliverables: 审核意见摘要
Blockers: 若 blocked，逐条列出
Judgment: 是否建议进入 30 执行 v0.6-a1
```
