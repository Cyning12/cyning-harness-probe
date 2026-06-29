# Invoke · 00 派工 · harness-probe Phase 1 全帽链

| 项 | 内容 |
| --- | --- |
| **task** | `docs/harness/tasks/done/task_harness_probe_phase1_full_hat_chain_v1.md` |
| **task_slug** | `harness-probe-phase1` |
| **hat** | `00` |
| **human_gate** | HG-TASK-DRAFT `approved` · HG-AUDIT-R1 `approved` |
| **freeze_id** | `HARNESS-PROBE-PHASE1-v1` |
| **日期** | 2026-06-29 |

## 派工摘要

本 task 由用户直接 kickoff，授权 00 Agent 全权签收人闸并主导执行到关账。跳过 20-task-audit R1，HG-TASK-DRAFT 和 HG-AUDIT-R1 由人显式授权 `approved`。

## 派工帽子序列

```text
00 派工（本 invoke）→ 30 执行（改代码 + 测试）→ 40 自检（跑命令 + 回填）→ 50 关账（review + checklist）
```

## 派工 Prompt（给 30 执行帽）

```text
你正在扮演 harness-probe 30 执行帽。

范围：
1. 在 src/builder.py 新增 build_hat_prompt 分发函数，实现 10-spec/10-task/20-review/50-reinspect 四顶帽子.
2. 在 src/models.py 扩展 HarnessTask 模型。
3. 在 src/probe.py 新增 --hat/--spec/--review-target/--mode/--run-output/--from-hat/--to-hat 参数。
4. 在 src/probe.py 新增 cmd_run（from/to hat 过滤）、cmd_watch（freeze_id 漂移检测）。
5. 在 src/orchestrator.py 改用 build_hat_prompt + handoff_summary。

验收：
- python -m src.probe compile --hat 10-spec/10-task/20-review/50-reinspect 均编译成功
- python -m src.probe run --from-hat 30 --to-hat 40 只执行指定范围
- python -m src.probe watch --once 检测一致性
- pytest tests/ -q 全绿

禁止：改帽链语义、接入真实 LLM、做 SDK 重构。
```
