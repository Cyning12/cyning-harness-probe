# Review · harness-probe Phase 4 Epic · R1 书面审

| 项 | 内容 |
| --- | --- |
| **task_slug** | `harness-probe-phase4-real-verify-runner-v1` |
| **审核帽** | 20-task-audit |
| **日期** | 2026-06-30 |
| **审核对象** | Epic + v0.6-a1 + v0.6-a2 + `docs/PLAN_PHASE4_v1_zh.md` |
| **最终 verdict** | **approved** |

---

## 1. Epic 拆分合理性

| 子任务 | 范围 | 依赖 | 判断 |
|--------|------|------|------|
| v0.6-a1 | SDK Executor 基础设施（协议 + SubprocessExecutor + Runner 接入 + 超时/截断 + 测试） | v0.5 | ✅ 边界清晰，可独立验收 |
| v0.6-a2 | CLI/MCP 参数透传 + 重跑 + audit blocked + 发布 | v0.6-a1 | ✅ 依赖正确，不提前耦合 |

**结论**：串行拆分合理，避免了同时修改 `harness_sdk/runner.py` 的冲突风险。

## 2. failure_paths 覆盖度

| Scenario ID | 覆盖情况 | 判断 |
|-------------|----------|------|
| `fp-verify-not-found` | Epic §3 / v0.6-a1 §3 / v0.6-a2 §3 均覆盖 | ✅ |
| `fp-verify-timeout` | v0.6-a1 D5 / §3 明确覆盖 | ✅ |
| `fp-verify-truncated` | v0.6-a1 D6 / §3 明确覆盖 | ✅ |
| `fp-retry-exhausted` | v0.6-a2 §3 覆盖 | ✅ |
| `fp-real-not-authorized` | Epic §4.5 / v0.6-a2 §3 覆盖 | ✅ |

**结论**：5 类核心失败路径均已覆盖。

## 3. 验收标准可执行性

- v0.6-a1 验收标准包含 `SubprocessExecutor.run(...)` 的具体 returncode 断言、超时断言、截断断言、Runner mock/real 切换断言。
- v0.6-a2 验收标准包含 CLI `--executor real --max-retries 2`、MCP `probe_run` 参数、audit `next_hat=30`、发布 tag。
- `test_strategy` 均为 `required`，并计划了 `tests/test_sdk_executor.py` 和端到端测试。

**结论**：验收标准可执行、可失败。

## 4. 范围 / 非范围

所有文档均明确：
- ✅ 不接入 LLM 自动修复
- ✅ 不引入 sandbox 隔离
- ✅ 不改帽链语义
- ✅ 不改业务 graph.json
- ✅ 不默认开启真实执行

**结论**：非范围明确，不会滑入 v0.8 / Runtime 领域。

## 5. human_gate 一致性

| task | HG-TASK-DRAFT | HG-AUDIT-R1 | blocks_hats | 判断 |
|------|---------------|-------------|-------------|------|
| Epic | approved | pending | 20-task-audit R1, 30 | ✅ |
| v0.6-a1 | approved | pending | 20-task-audit R1, 30 | ✅ |
| v0.6-a2 | pending | pending | 20-task-audit R1, 30 | ✅（v0.6-a2 待 a1 完成后再签） |

**结论**：HG-AUDIT-R1 正确阻塞 30；v0.6-a2 的 HG-TASK-DRAFT 可后续在 a1 关账后由 00 签。

## 6. 关键人类验收节点

| 节点 | 内容 | 判断 |
|------|------|------|
| R1 | task 书面审（本 review） | ✅ 完整 |
| R2 | v0.6-a1 代码审 | ✅ 明确 |
| R3 | v0.6-a1 合并前 CI | ✅ 明确 |
| R4 | v0.6-a2 代码审 | ✅ 明确 |
| R5 | v0.6 发布 | ✅ 明确 |

---

## 小建议（非阻塞）

1. v0.6-a1 的 `SubprocessExecutor` 建议默认使用 `asyncio.create_subprocess_exec` 而非 `shell`，以降低注入风险；如果必须用 `shell=True`，应在 failure_paths 中增加命令注入风险提示。
2. v0.6-a2 的 `--cwd` 参数在 MCP Tool 中建议校验路径存在性，避免静默失败。

---

## 最终结论

**Status: approved**

本 Epic 及 v0.6-a1 / v0.6-a2 子任务通过 R1 书面审。HG-AUDIT-R1 视为可 approved，可进入 **30 执行 v0.6-a1**。

---

## 修订记录

| 版本 | 日期 | 说明 |
| --- | --- | --- |
| v1 | 2026-06-30 | R1 书面审 · approved |
