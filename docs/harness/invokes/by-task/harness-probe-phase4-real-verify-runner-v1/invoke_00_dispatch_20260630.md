# Invoke · 00 派工 · harness-probe Phase 4 真执行验证（Epic）

| 项 | 内容 |
| --- | --- |
| **task** | `docs/harness/tasks/active/task_harness_probe_phase4_real_verify_runner_v1.md` |
| **task_slug** | `harness-probe-phase4-real-verify-runner-v1` |
| **hat** | `00` |
| **human_gate** | HG-TASK-DRAFT **`approved`** · HG-AUDIT-R1 `pending` |
| **freeze_id** | `HARNESS-PROBE-PHASE4-v1` |
| **日期** | 2026-06-30 |

## 派工摘要

本 Epic 由 00 统筹根据用户授权启动，已拆分为两个串行子任务：

1. **v0.6-a1**：SDK Executor 基础设施
2. **v0.6-a2**：CLI/MCP 集成 + 发布

执行顺序：**串行**。v0.6-a2 必须等 v0.6-a1 合并到 main 后才能开工。

HG-TASK-DRAFT 已 approved。下一步进入 **20-task-audit R1** 书面审。

## 派工帽子序列

```text
00 派工（本 invoke）
  → 20-task-audit R1（审核 Epic + v0.6-a1 + v0.6-a2）
  → 30 执行 v0.6-a1
  → 40 自检 v0.6-a1
  → 50 关账 v0.6-a1
  → 30 执行 v0.6-a2
  → 40 自检 v0.6-a2
  → 50 关账 v0.6-a2
```

## 00 派工 Prompt（已执行）

```text
将 Phase 4 拆分为两个串行子任务：
1. v0.6-a1 SDK Executor 基础设施（harness_sdk/executor.py + runner 接入 + 测试）
2. v0.6-a2 CLI/MCP 集成与发布（CLI 参数透传 + MCP Tool 扩展 + 重跑 + audit blocked + v0.6 发布）

更新父 Epic task，明确串行依赖和关键人类验收节点（R1 task 审 / R2 a1 代码审 / R3 a1 合并 / R4 a2 代码审 / R5 v0.6 发布）。

将 HG-TASK-DRAFT 标记为 approved，准备 spawn 20-task-audit R1。
```
