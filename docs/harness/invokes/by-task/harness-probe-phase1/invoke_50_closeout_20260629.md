# Invoke · 50 关账 · harness-probe Phase 1 全帽链

| 项 | 内容 |
| --- | --- |
| **task** | `docs/harness/tasks/done/task_harness_probe_phase1_full_hat_chain_v1.md` |
| **task_slug** | `harness-probe-phase1` |
| **hat** | `50` |
| **上一帽** | [`invoke_40_selfcheck_20260629.md`](./invoke_40_selfcheck_20260629.md) |
| **日期** | 2026-06-29 |

## 验收表

| ref | pass/fail | evidence |
| --- | --- | --- |
| D1 | pass | `src/builder.py` · `build_hat_prompt` 分发 6 hat |
| D2 | pass | 10-spec prompt 含 R0-R5 + Delta |
| D3 | pass | 10-task prompt 含 SPEC 映射 + task 骨架 |
| D4 | pass | 20-review prompt 含 approved/blocked + HG-AUDIT-R1 |
| D5 | pass | 50-reinspect prompt 含 failure_path_ref + global/independent |
| D6 | pass | run --from-hat 30 --to-hat 40 只执行范围帽子 |
| D7 | pass | watch --once freeze_id 一致性检测 |
| D8 | pass | --hat/--spec/--review-target/--mode/--run-output 参数工作 |
| D9 | pass | models.py 扩展 5 个字段不影响现有测试 |

## 关账结论

**CLOSE** · 12/12 验收项全部 pass。Phase 1 全帽链补齐完成。

## 跨仓 commit 清单

| 仓 | commit | 说明 |
|----|--------|------|
| `harness-probe` | `8b23630` | feat(phase1): 全帽链支持 |
| `harness-probe` | `d0dd227` | chore(release): v0.3 · closeout docs |

## 关联

- 工作区对照：`Projects/docs/harness/prompts/PROMPT_cursor_task_chain_serial_v1.md` v1.1
- 长程规划 phase docs：`docs/PLAN_PHASE1_v1_zh.md` / `docs/PLAN_SDK_REFACTOR_v1_zh.md` / `docs/PLAN_MCP_SERVER_v1_zh.md`
