# Task · harness-probe Phase 1 · 全帽链补齐 + 模拟执行 + 漂移检测（v1）

> **状态**：`done` · 2026-06-29 全链关账  
> **task_slug**：`harness-probe-phase1`  
> **方案真值**：[`docs/PLAN_PHASE1_v1_zh.md`](../../PLAN_PHASE1_v1_zh.md)  
> **关联**：工作区 `COMPARISON_tech_graph_coding_wiki_graph_memory_v1_zh.md` §2.2 · `PROMPT_cursor_task_chain_serial_v1.md` v1.1  
> **invoke**：[`docs/harness/invokes/by-task/harness-probe-phase1/README.md`](../../invokes/by-task/harness-probe-phase1/README.md)

---

## Harness 元信息（执行 Agent 必读）

| 字段 | 值 |
| --- | --- |
| **track** | `feature` |
| **lightweight_task** | `no`（须 R0–R5 完整思考轮） |
| **module_id** | `none` |
| **graph_delta** | `none` |
| **graph_delta_note** | 纯 harness-probe 代码与文档；不触业务 `_tech_graph` |
| **graph_gate** | `n/a` |
| **test_strategy** | `recommended` |
| **test_strategy_note** | 无运行时代码；以 `pytest tests/ -q` + 手动 CLI 验证 |
| **freeze_id** | `HARNESS-PROBE-PHASE1-v1` |
| **gates_before_code** | `["failure_paths", "freeze_id", "human_gate"]` |
| **orchestration** | Cursor Task 链 |
| **semi_auto** | `false`（deprecated） |
| **audit_profile** | `full` |
| **git_branch** | `main`（探针仓无 task 分支纪律） |
| **worktree_root** | `harness-probe/` |
| **experience_capture** | `recommended` |
| **kpi_rubric** | `KPI_RUBRIC_v1_2` |
| **kpi_aggregator** | `CLOSE` |
| **code_quality_bar** | `src/ + tests/` |

### 人工闸 `human_gate`

| human_gate_id | status | blocks_hats | 说明 |
| --- | --- | --- | --- |
| HG-TASK-DRAFT | approved | 20-task-audit R1, 30 | 00 起草 · 人签 |
| HG-AUDIT-R1 | approved | 30 | 20-task-audit R1 通过 · 人签 |

---

## 1. 背景与目标

harness-probe v0.2 仅支持 30/40 两顶帽子编译。Phase 1 目标：补齐 10-spec / 10-task / 20-review / 50-reinspect 四顶新帽，新增 `--run` 模拟执行与 `--watch` freeze_id 漂移检测。不改帽链语义，只做编译前端对齐。

---

## 2. 范围

### 必须交付

| ID | 交付物 | 位置 | 验收 |
| --- | --- | --- | --- |
| D1 | `build_hat_prompt` 分发函数 | `src/builder.py` | 按帽生成对应 Prompt |
| D2 | 10-spec prompt builder | `src/builder.py :: _build_10_spec_prompt` | 含 R0–R5、§1–§6 结构 |
| D3 | 10-task prompt builder | `src/builder.py :: _build_10_task_prompt` | 含 SPEC 映射 + task 骨架 |
| D4 | 20-review prompt builder | `src/builder.py :: _build_20_review_prompt` | 含 approved/blocked + HG-AUDIT-R1 |
| D5 | 50-reinspect prompt builder | `src/builder.py :: _build_50_reinspect_prompt` | 含 failure_path_ref + global/independent |
| D6 | `--run` 模拟执行 | `src/orchestrator.py` + `src/probe.py :: cmd_run` | from/to hat 过滤 + task_run JSON |
| D7 | `--watch` 漂移检测 | `src/probe.py :: cmd_watch` | freeze_id 一致性检测 |
| D8 | CLI 新增参数 | `src/probe.py` | `--hat/--spec/--review-target/--mode/--run-output` |
| D9 | 模型扩展 | `src/models.py` | `spec_path/spec_text/review_target/run_output_path/reinspect_mode` |

### 明确不做

- 不改帽链语义
- 不接入真实 LLM
- 不在本 task 内做 SDK 重构

---

## 3. 失败路径

| # | Scenario ID | 触发条件 | 系统行为 | 可重试 | 用户可见 |
| --- | --- | --- | --- | --- | --- |
| F1 | `fp-unsupported-hat` | 传入未实现的 hat 值 | `ValueError("Unsupported hat: {hat}")` | 修正参数 | CLI 报错 |
| F2 | `fp-drift-silent` | `watch --once` 发现漂移但误报 | 影响面分析不准确 | 重跑 | 误告警或漏告警 |
| F3 | `fp-handoff-stale` | 上一帽摘要传递丢失 | 生成的下一棒 Prompt 缺上下文 | yes | Prompt 缺 handoff 信息 |

---

## 4. 验收标准

- [x] `python -m src.probe compile --hat 10-spec --quiet` 生成合法 Prompt
- [x] `python -m src.probe compile --hat 10-task --spec data/tasks/sample_task.md --quiet` 含 SPEC 映射
- [x] `python -m src.probe compile --hat 20-review --review-target task --quiet` 含 HG-AUDIT-R1
- [x] `python -m src.probe compile --hat 50-reinspect --mode global --quiet` 含 failure_path_ref
- [x] `python -m src.probe run --from-hat 30 --to-hat 40 --quiet` 只执行范围帽子
- [x] `python -m src.probe watch --once --entry RAG` 检测 freeze_id 一致性
- [x] `pytest tests/ -q` 全绿（11 passed）

---

## 5. 依赖

- upstream：工作区 PROMPT v1.1（COMPARISON §2.2、PRE_SPAWN_VERIFY）
- 前置 commit：harness-probe v0.2（`5dae3af`）

---

## 6. 自检结论（执行者）

| # | 验收项 | 结果 | 证据 |
| --- | --- | --- | --- |
| V1 | 10-spec prompt 编译 | pass | `outputs/prompt_*_hat10-spec.md` |
| V2 | 10-task prompt 编译 | pass | `outputs/prompt_*_hat10-task.md` |
| V3 | 20-review prompt 编译 | pass | `outputs/prompt_*_hat20-review.md` |
| V4 | 50-reinspect prompt 编译 | pass | `outputs/prompt_*_hat50-reinspect.md` |
| V5 | run from/to hat 过滤 | pass | session `b72124ff93a5` nodes=[('30','done'),('40','done')] |
| V6 | watch once 漂移检测 | pass | `graph=HARNESS-PROBE-SAMPLE-V0.1 task=HARNESS-PROBE-SAMPLE-V0.1 ✅` |
| V7 | pytest | pass | 11 passed |

---

## 7. 修订记录

| 版本 | 日期 | 说明 |
| --- | --- | --- |
| v1 | 2026-06-29 | 00 起草 · 30 执行 · 40 自检 · 50 关账 |
