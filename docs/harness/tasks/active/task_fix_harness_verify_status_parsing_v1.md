# task_fix_harness_verify_status_parsing_v1

## Harness 元信息

| 字段 | 值 |
| --- | --- |
| **track** | `bugfix` |
| **lightweight_task** | `yes` |
| **module_id** | `HARNESS-VERIFY` |
| **graph_delta** | `none` |
| **test_strategy** | `required` |
| **freeze_id** | `HARNESS-PROBE-PHASE5-v1` |
| **gates_before_code** | `["human_gate"]` |
| **orchestration** | 30 直接修复 |
| **git_branch** | `task/fix-harness-verify-status-parsing-v1` |
| **worktree_root** | `harness-probe/` |
| **task_slug** | `fix-harness-verify-status-parsing-v1` |
| **status** | `approved` |
| **target_version** | `@cyning/harness` 2.1.0 |
| **parent_epic** | 无 |
| **date** | `2026-06-30` |

### 人工闸 `human_gate`

| human_gate_id | status | blocks_hats | 说明 |
| --- | --- | --- | --- |
| HG-TASK-DRAFT | `approved` | 30 | 任务单定稿 |
| HG-EXEC-AUTH | `approved` | 30 | 授权直接修复产品包 |

## 背景与目标

`npx @cyning/harness verify`（产品包 2.1.0）在解析 task 人工闸表时，将 status 字段的 Markdown 反引号一并捕获，导致 `evaluateMayStart30` 判定 `HG-AUDIT-R1` 非 approved，即使 task 表已明确写 `approved`。

目标：修复 `@cyning/harness` 产品包中的 `lib/task-meta.js`，使 `normalizeCell` 正确去除反引号，从而正确识别 `approved` 状态。

## 范围

- 修改 `~/.npm/_npx/<hash>/node_modules/@cyning/harness/lib/task-meta.js`
  - 修复 `normalizeCell` 函数，去除反引号
  - 或修复 `parseHumanGates` 中的 status 解析
- 验证：修复后 `npx @cyning/harness verify --target . --task docs/harness/tasks/active/task_harness_probe_phase5_safety_executor_v1.md` 输出 `may_start_30: true`

## 非范围

- 不修改 harness-probe 业务代码
- 不修改 task 单内容
- 不发布 npm 包（由用户手动发布）

## 依赖

- 已定位问题文件：`/Users/cyning/.npm/_npx/58434e3517750671/node_modules/@cyning/harness/lib/task-meta.js`
- 已确认 task 表格式正确、review 文件命名正确

## 验收标准

- [ ] 修复 `normalizeCell` 去除反引号
- [ ] 修复后 `npx @cyning/harness verify` 对 Phase 5 task 输出 `may_start_30: true`
- [ ] 不破坏对其他 task 的解析

## 失败路径

| ID | 触发条件 | 系统行为 | 可重试 | 用户可见 |
| --- | --- | --- | --- | --- |
| F1 | 修复后仍误判 | 继续排查 `parseHumanGates` 正则 | 是 | 输出调试信息 |
| F2 | 产品包路径变化 | 重新定位 npx 缓存路径 | 是 | 提示用户 |

## 实现备忘

- 待执行

## 测试策略

`required`。修复后必须运行 `npx @cyning/harness verify` 验证通过。

## 自检结论（执行者）

- 待回填

## 修订记录

| 版本 | 日期 | 说明 |
| --- | --- | --- |
| v1 | 2026-06-30 | 初稿 |
