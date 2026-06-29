# Phase 1 关账 · 全帽链补齐 + 模拟执行（R1 · 2026-06-29）

| 项 | 内容 |
| --- | --- |
| **状态** | `done` · Phase 1 fully closed |
| **范围** | harness-probe Phase 1：10-spec / 10-task / 20-review / 50-reinspect 帽子 + `--run` 模拟执行 + `--watch` 漂移检测 |
| **前置** | Probe v0.2 |
| **目标版本** | v0.3 |
| **日期** | 2026-06-29 |
| **实现 commit** | `8b23630` |

---

## 1. 阶段成果 checklist

### 帽子补齐

| 帽子 | 命令 | 状态 | 验证 |
| --- | --- | --- | --- |
| 10-spec | `python -m src.probe compile --hat 10-spec` | ✅ done | 生成 SPEC 草案 Prompt，含 R0-R5、§1-§6 结构 |
| 10-task | `python -m src.probe compile --hat 10-task --spec <path>` | ✅ done | 生成 task 骨架 Prompt，含 Harness 元信息、failure_paths 映射 |
| 20-review | `python -m src.probe compile --hat 20-review --review-target task\|spec` | ✅ done | 生成审核 Prompt，含 approved/blocked + HG-AUDIT-R1 签收 |
| 30 | `python -m src.probe compile --hat 30` | ✅ 已有 | execution hat prompt（v0.1 即支持） |
| 40 | `python -m src.probe compile --hat 40` | ✅ 已有 | self-check hat prompt（v0.1 即支持） |
| 50-reinspect | `python -m src.probe compile --hat 50-reinspect --mode independent\|global` | ✅ done | 生成复检 Prompt，含 failure_path_ref 表 + merge 建议 |

### 命令新增

| 命令 | 功能 | 状态 | 验证 |
| --- | --- | --- | --- |
| `compile --hat` | 指定帽子编译 | ✅ done | 支持逗号分隔多帽，如 `--hat 10-spec,20-review` |
| `compile --spec` | 10-task 关联 SPEC | ✅ done | 读取 SPEC 文件注入 prompt |
| `compile --review-target` | 20-review 审核对象 | ✅ done | task / spec |
| `compile --mode` | 50-reinspect 模式 | ✅ done | independent / global |
| `compile --run-output` | 50-reinspect 关联运行记录 | ✅ done | 注入 task_run JSON 路径 |
| `run --from-hat/--to-hat` | 模拟执行帽子范围 | ✅ done | 只执行 from-to 之间的帽子 |
| `watch --once/--interval` | freeze_id 漂移检测 | ✅ done | 检测 graph 与 task freeze_id 一致性 |

### 关键模块变更

| 文件 | 改动摘要 |
| --- | --- |
| `src/builder.py` | 新增 `build_hat_prompt` 分发函数 + 4 顶新帽 builder；原有 30/40 builder 保留 |
| `src/models.py` | `HarnessTask` 新增 `spec_path`/`spec_text`/`review_target`/`run_output_path`/`reinspect_mode` |
| `src/probe.py` | 新增 `cmd_run`（from/to hat 过滤）、`cmd_watch`；compile/run 子命令新增 --spec/--review-target/--mode/--run-output 参数 |
| `src/orchestrator.py` | 改用 `build_hat_prompt`+`handoff_summary`；支持 `from_hat`/`to_hat` 过滤 |
| `tests/test_probe.py` | 新增 4 个 hat builder 测试；全量 11 passed |

### 对比 Phase 1 计划（`docs/PLAN_PHASE1_v1_zh.md`）

| 计划项 | 达成 | 说明 |
| --- | --- | --- |
| 10-spec prompt 编译 | ✅ | 含 R0-R5 + Delta + 验收标准结构 |
| 10-task prompt 编译 | ✅ | 含 SPEC 映射 + failure_paths 生成 |
| 20-review prompt 编译 | ✅ | 含 approved/blocked 签收逻辑 + 下一棒 Prompt |
| 50-reinspect prompt 编译 | ✅ | 含 failure_path_ref 表 + independent/global 双模式 |
| `--run` 模拟执行 | ✅ | `run_task` 支持 from/to hat 过滤 |
| `--watch` 漂移检测 | ✅ | 检测 graph/task freeze_id 一致性 |
| 测试覆盖率 | ✅ | 11 passed，核心 builder 函数全覆盖 |

---

## 2. 验收命令

```bash
cd /Users/cyning/Desktop/Projects/harness-probe

# 单元测试
python -m pytest tests/ -q                          # 11 passed

# 10-spec 编译
python -m src.probe compile --hat 10-spec --quiet   #✅

# 10-task 编译
python -m src.probe compile --hat 10-task --quiet   #✅

# 20-review 编译（task 审核）
python -m src.probe compile --hat 20-review --review-target task --quiet  #✅

# 50-reinspect 编译（global 模式）
python -m src.probe compile --hat 50-reinspect --mode global --quiet  #✅

# 串行运行 10-spec→20-review→30→40→50-reinspect
python -m src.probe run \
  --hat 10-spec,10-task,20-review,30,40,50-reinspect \
  --from-hat 30 --to-hat 40 \
  --review-target task --mode global --quiet
# → nodes: [('30', 'done'), ('40', 'done')]

# freeze_id 漂移检测
python -m src.probe watch --once --entry RAG
# → graph=HARNESS-PROBE-SAMPLE-V0.1 task=HARNESS-PROBE-SAMPLE-V0.1 ✅ 一致
```

---

## 3. 修订记录

| 版本 | 日期 | 说明 |
| --- | --- | --- |
| v1 | 2026-06-29 | Phase 1 fully closed · 6 帽 + --run + --watch |
