# Invoke · 30 执行 · harness-probe v0.6-a1 SDK Executor 基础设施

| 项 | 内容 |
| --- | --- |
| **task** | `docs/harness/tasks/active/task_harness_probe_phase4_a1_sdk_executor_v1.md` |
| **task_slug** | `harness-probe-phase4-a1-sdk-executor-v1` |
| **hat** | `30` |
| **human_gate** | HG-TASK-DRAFT `approved` · HG-AUDIT-R1 `approved` |
| **freeze_id** | `HARNESS-PROBE-PHASE4-v1` |
| **日期** | 2026-06-30 |
| **审核产出** | [`docs/harness/reviews/REVIEW_task_harness_probe_phase4_real_verify_runner_v1_R1_20260630.md`](../../reviews/REVIEW_task_harness_probe_phase4_real_verify_runner_v1_R1_20260630.md) |

## 30 执行 Prompt

```text
你正在扮演 harness-probe 30 执行帽。

范围（v0.6-a1）：
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
