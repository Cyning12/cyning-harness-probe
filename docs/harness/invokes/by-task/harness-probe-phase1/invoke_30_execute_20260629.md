# Invoke · 30 执行 · harness-probe Phase 1 全帽链

| 项 | 内容 |
| --- | --- |
| **task** | `docs/harness/tasks/done/task_harness_probe_phase1_full_hat_chain_v1.md` |
| **task_slug** | `harness-probe-phase1` |
| **hat** | `30` |
| **上一帽** | [`invoke_00_dispatch_20260629.md`](./invoke_00_dispatch_20260629.md) |
| **日期** | 2026-06-29 |

## 改动文件

| 文件 | 改动摘要 |
| --- | --- |
| `src/builder.py` | 新增 `build_hat_prompt` 分发 + `_build_10_spec_prompt` / `_build_10_task_prompt` / `_build_20_review_prompt` / `_build_50_reinspect_prompt`；保留原 30/40 builder |
| `src/models.py` | `HarnessTask` 新增 `spec_path` / `spec_text` / `review_target` / `run_output_path` / `reinspect_mode` |
| `src/probe.py` | 新增 `cmd_run`（from/to hat 过滤）、`cmd_watch`（freeze_id 漂移）；compile/run 新增 `--hat/--spec/--review-target/--mode/--run-output/--from-hat/--to-hat` |
| `src/orchestrator.py` | 改用 `build_hat_prompt` + `handoff_summary`；新增 `from_hat`/`to_hat` 过滤 |
| `tests/test_probe.py` | 新增 4 个 hat builder 测试 |

## 验证

```bash
cd /Users/cyning/Desktop/Projects/harness-probe

# 各帽编译验证
python -m src.probe compile --hat 10-spec --quiet
python -m src.probe compile --hat 10-task --quiet
python -m src.probe compile --hat 20-review --review-target task --quiet
python -m src.probe compile --hat 50-reinspect --mode global --quiet

# 模拟执行过滤
python -m src.probe run \
  --hat 10-spec,10-task,20-review,30,40,50-reinspect \
  --from-hat 30 --to-hat 40 --quiet
# → nodes: [('30', 'done'), ('40', 'done')]

# 漂移检测
python -m src.probe watch --once --entry RAG
# → graph=HARNESS-PROBE-SAMPLE-V0.1 task=HARNESS-PROBE-SAMPLE-V0.1 ✅ 一致

# 单测
pytest tests/ -q  # 11 passed
```

## 交接给 40

下一棒：40 自检，运行上述验证命令并回填 task `### 自检结论`。
