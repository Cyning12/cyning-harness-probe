# Invoke · 40 自检 · harness-probe Phase 1 全帽链

| 项 | 内容 |
| --- | --- |
| **task** | `docs/harness/tasks/done/task_harness_probe_phase1_full_hat_chain_v1.md` |
| **task_slug** | `harness-probe-phase1` |
| **hat** | `40` |
| **上一帽** | [`invoke_30_execute_20260629.md`](./invoke_30_execute_20260629.md) |
| **日期** | 2026-06-29 |

## 自检项

| # | 验收项 | 结果 | 证据 |
| --- | --- | --- | --- |
| V1 | 10-spec prompt 编译 | **pass** | `outputs/prompt_*_hat10-spec.md` 含 R0–R5、SPEC 草案 |
| V2 | 10-task prompt 编译 | **pass** | `outputs/prompt_*_hat10-task.md` 含 task.md 骨架 |
| V3 | 20-review prompt 编译 | **pass** | `outputs/prompt_*_hat20-review.md` 含 approved/blocked + HG-AUDIT-R1 |
| V4 | 50-reinspect prompt 编译 | **pass** | `outputs/prompt_*_hat50-reinspect.md` 含 failure_path_ref + global/independent |
| V5 | run from/to hat 过滤 | **pass** | session `b72124ff93a5` nodes=[('30','done'),('40','done')] |
| V6 | watch once 漂移检测 | **pass** | `graph=HARNESS-PROBE-SAMPLE-V0.1 task=HARNESS-PROBE-SAMPLE-V0.1 ✅` |
| V7 | pytest 全量 | **pass** | 11 passed in 0.05s |

## 命令记录

```bash
cd /Users/cyning/Desktop/Projects/harness-probe

# 编译验证
python -m src.probe compile --hat 10-spec --quiet
python -m src.probe compile --hat 10-task --quiet
python -m src.probe compile --hat 20-review --review-target task --quiet
python -m src.probe compile --hat 50-reinspect --mode global --quiet

# 模拟执行
python -m src.probe run \
  --hat 10-spec,10-task,20-review,30,40,50-reinspect \
  --from-hat 30 --to-hat 40 --quiet

# 漂移检测
python -m src.probe watch --once --entry RAG

# 单测
pytest tests/ -q
```

## 自检结论

全部验收项 pass。已回填 task §6 自检表。无 blocking。交接给 50 关账。
