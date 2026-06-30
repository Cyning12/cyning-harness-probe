# Invoke · 00 统筹派工 + 关账 · harness-probe Phase 4 真执行验证

| 项 | 内容 |
| --- | --- |
| **task** | `docs/harness/tasks/active/task_harness_probe_phase4_real_verify_runner_v1.md` |
| **task_slug** | `harness-probe-phase4-real-verify-runner-v1` |
| **hat** | `00` |
| **human_gate** | HG-TASK-DRAFT `approved` · HG-AUDIT-R1 `approved` |
| **freeze_id** | `HARNESS-PROBE-PHASE4-v1` |
| **日期** | 2026-06-30 |
| **审核产出** | [`docs/harness/reviews/REVIEW_task_harness_probe_phase4_real_verify_runner_v1_R1_20260630.md`](../../reviews/REVIEW_task_harness_probe_phase4_real_verify_runner_v1_R1_20260630.md) |

## 派工摘要

Phase 4 Epic 已通过 R1 书面审，HG-AUDIT-R1 approved。本 invoke 由 00 统筹一次性派工完整帽链，并负责最终关账。

执行纪律：
- 全程在 `harness-probe/` 工作树执行
- v0.6-a1 与 v0.6-a2 **串行**：a2 必须等 a1 合并到 main 后开工
- 每阶段 30 改码前必须再次扫描 task 人工闸表
- 每阶段 50 关账前必须独立跑全量 `pytest tests/ -q`

## 完整帽子链

```text
00 统筹派工（本 invoke）
  → 30 执行 v0.6-a1（SDK Executor）
  → 40 自检 v0.6-a1
  → 50 关账 v0.6-a1
  → [合并 a1 到 main]
  → 30 执行 v0.6-a2（CLI/MCP 集成 + 发布）
  → 40 自检 v0.6-a2
  → 50 关账 v0.6-a2
  → [合并 a2 到 main，打 tag v0.6.0]
  → 00 最终关账
```

---

## 30 执行 · v0.6-a1 SDK Executor

**task**：[`docs/harness/tasks/active/task_harness_probe_phase4_a1_sdk_executor_v1.md`](../../tasks/active/task_harness_probe_phase4_a1_sdk_executor_v1.md)

### Prompt

```text
你正在扮演 harness-probe 30 执行帽。

范围：
1. 在 harness_sdk/ 新增 executor.py：
   - 定义 VerifyExecutor Protocol（async run(cmd, cwd) -> ExecutionResult）
   - 实现 SubprocessExecutor，使用 asyncio.create_subprocess_shell
   - 支持 timeout 参数（默认 60s）
   - 支持 stdout 截断（> 4K 时加 [truncated] 标记）
2. 在 harness_sdk/models.py 新增 ExecutionResult 数据类：
   - returncode: int
   - stdout: str
   - stderr: str
   - elapsed_ms: int
3. 改造 harness_sdk/runner.py：
   - TaskRunner.__init__ 增加 executor: VerifyExecutor | None = None
   - _execute_hat 按 executor 分发：None -> mock；SubprocessExecutor -> 真实执行 contract.verify
   - 保持默认 mock 行为不变
4. 新增 tests/test_sdk_executor.py，覆盖：
   - mock 模式保持 v0.5 行为
   - SubprocessExecutor 执行 echo ok / exit 1
   - 超时命令处理
   - 输出截断
   - TaskRunner(executor=SubprocessExecutor()) 真实执行 contract.verify

验收：
- pytest tests/test_sdk_executor.py -q 全绿
- pytest tests/ -q 全绿（≥ 36 个基线）
- python -m harness_probe.cli run --from-hat 30 --to-hat 40 默认 mock，行为与 v0.5 一致

禁止：
- 不重试逻辑（归 v0.6-a2）
- 不改 CLI / MCP
- 不接入 LLM / sandbox
- 不改帽链语义 / graph.json
```

---

## 40 自检 · v0.6-a1

### Prompt

```text
你正在扮演 harness-probe 40 自检帽。

任务：对 v0.6-a1 执行结果做自检。

必做：
1. 运行 pytest tests/ -q，确认全绿
2. 运行 python -m harness_probe.cli verify --task data/tasks/sample_task.md
3. 运行 python -m harness_probe.cli run --from-hat 30 --to-hat 40 --quiet
4. 检查 harness_sdk/executor.py 无文件 IO、无 print、无环境变量访问
5. 检查 runner.py 的 executor 注入是否符合"默认 mock、显式 real"原则
6. 回填 task 文件 §7 自检结论表（V1–V6）

若失败：回滚到 30，不要进入 50 关账。
```

---

## 50 关账 · v0.6-a1

### Prompt

```text
你正在扮演 harness-probe 50 关账帽。

任务：v0.6-a1 关账。

必做：
1. 复核 task 验收标准是否全部勾选
2. 复核自检表是否全部 pass
3. 生成 invoke_50_closeout_a1_*.md 落盘
4. 若全部通过，输出 "CLOSE · 可合并到 main"
5. 若未通过，输出打回目标（30）和缺口清单

关账后由 00 合并到 main。
```

---

## 30 执行 · v0.6-a2 CLI/MCP 集成 + 发布

**task**：[`docs/harness/tasks/active/task_harness_probe_phase4_a2_cli_mcp_integration_v1.md`](../../tasks/active/task_harness_probe_phase4_a2_cli_mcp_integration_v1.md)

**前置**：v0.6-a1 已合并到 main

### Prompt

```text
你正在扮演 harness-probe 30 执行帽。

范围：
1. 在 harness_probe/cli.py 的 cmd_run / cmd_compile 增加参数：
   - --executor {mock,real}（默认 mock）
   - --max-retries N（默认 0）
   - --cwd PATH
2. 在 harness_sdk/runner.py 增加 max_retries 逻辑：
   - 失败时重跑最多 N 次
   - 重跑耗尽后 run_node.status = blocked
3. 在 harness_mcp/tools.py 扩展 probe_run：
   - executor: str = "mock"
   - max_retries: int = 0
   - cwd: str | None = None
4. 改造 harness_mcp/tools.py 的 probe_audit：
   - 识别 blocked 节点
   - 输出 verdict=fail、recommendation=打回至 30、next_hat=30
5. 更新 README.md / CHANGELOG.md 到 v0.6
6. 更新 pyproject.toml 和 harness_probe/__init__.py 版本到 0.6.0
7. 新增/扩展测试：
   - tests/test_cli.py：--executor real、--max-retries
   - tests/test_mcp_tools.py：probe_run executor/real、probe_audit blocked

验收：
- python -m harness_probe.cli run --executor real --max-retries 2 --from-hat 30 --to-hat 40 真实执行并支持重跑
- 重跑耗尽后节点 blocked
- MCP probe_run 支持 executor="real"、max_retries=2
- pytest tests/ -q 全绿
- 可成功打 tag v0.6.0 并 push

禁止：
- 不接入 LLM 自动修复
- 不引入 sandbox 隔离
- 不改帽链语义 / graph.json
- 不默认开启真实执行
```

---

## 40 自检 · v0.6-a2

### Prompt

```text
你正在扮演 harness-probe 40 自检帽。

任务：对 v0.6-a2 执行结果做自检。

必做：
1. 运行 pytest tests/ -q，确认全绿
2. 运行 python -m harness_probe.cli run --executor real --max-retries 1 --from-hat 30 --to-hat 40 --quiet
3. 运行 MCP probe_run / probe_audit 测试
4. 验证默认 --executor mock 行为与 v0.5 一致
5. 验证 VERSION bump 正确
6. 回填 task 文件 §7 自检结论表

若失败：回滚到 30，不要进入 50 关账。
```

---

## 50 关账 · v0.6-a2

### Prompt

```text
你正在扮演 harness-probe 50 关账帽。

任务：v0.6-a2 关账 + v0.6 发布。

必做：
1. 复核 task 验收标准是否全部勾选
2. 复核自检表是否全部 pass
3. 生成 invoke_50_closeout_a2_*.md 落盘
4. 若全部通过，执行：
   - git tag v0.6.0
   - git push origin main v0.6.0
5. 输出 "CLOSE · v0.6 已发布"
6. 若未通过，输出打回目标（30）和缺口清单
```

---

## 00 最终关账

### Prompt

```text
你正在扮演 harness-probe 00 统筹。

任务：Phase 4 Epic 最终关账。

必做：
1. 汇总 v0.6-a1 + v0.6-a2 的所有 commit、tag、测试报告
2. 更新 docs/harness/tasks/active/ 下 Epic + 子 task 状态为 done
3. 将 done task 归档到 docs/harness/tasks/done/
4. 更新 docs/harness/invokes/by-task/harness-probe-phase4-real-verify-runner-v1/README.md 帽链状态
5. 生成最终 review 文档并落盘 reviews/
6. 向用户报告 Phase 4 完成摘要
```

---

## 关键人类验收节点（ recap ）

| 节点 | 状态 | 说明 |
|------|------|------|
| R1 · task 书面审 | ✅ approved | 已完成 |
| R2 · a1 代码审 | pending | a1 40 自检后由人审 |
| R3 · a1 合并前 | pending | CI 全绿 |
| R4 · a2 代码审 | pending | a2 40 自检后由人审 |
| R5 · v0.6 发布 | pending | a2 50 关账后 |

---

## 修订记录

| 版本 | 日期 | 说明 |
| --- | --- | --- |
| v1 | 2026-06-30 | 00 统筹 · Phase 4 完整派工 + 关账 Prompt |
