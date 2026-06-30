# Phase 5 里程碑总结 · harness-probe v0.7.0

## 元信息

| 字段 | 值 |
| --- | --- |
| 日期 | 2026-06-30 |
| 版本 | v0.7.0 |
| 前置版本 | v0.6.0 |
| 产品包 | `@cyning/harness` 2.1.1 |
| 任务单 | `docs/harness/tasks/active/task_harness_probe_phase5_safety_executor_v1.md` |
| 合并 commit | `a392da7` |
| tag | `v0.7.0` |

## 本次交付内容

### 1. 产品包热修复（@cyning/harness 2.1.1）

- **问题**：`npx @cyning/harness verify` 解析 task 人工闸表时，未去除 Markdown 反引号，导致 `` `approved` `` 被误判为 `pending`，30 执行帽无法开工。
- **修复**：
  - `lib/task-meta.js`：`normalizeCell` 去除反引号与星号
  - `wizard/gate-check.sh`：`gate_status` / `gate_blocks` 的 awk 去除反引号与星号
- **验证**：`npm test` 72 passed；所有 active task 均可正常通过 verify
- **文档**：新增 postmortem `cyning-harness/docs/methodology/execution/POSTMORTEM_backtick_gate_parsing_v1_zh.md`

### 2. harness-probe v0.7.0 安全执行器

#### 新增能力

| 能力 | 说明 |
| --- | --- |
| 命令白名单 | 默认允许 `pytest`、`python -m pytest`、`python -m harness_probe.cli`、`echo`、`cat`、`ls`、`pwd`、`git status/diff/log` |
| 危险字符黑名单 | `$()`、`${}`、`&&`、`||`、`>>`、`` ` ``、`;`、`|`、`>`、`<`、`*`、`?` |
| 危险命令前缀黑名单 | `rm`、`mv`、`cp`、`sudo`、`su`、`chmod`、`chown`、`curl`、`wget`、`ssh`、`scp`、`eval`、`exec`、`source`、`. ` |
| 三模式安全策略 | `whitelist`（默认）/ `audit` / `unsafe` |
| dry-run | `--dry-run` 不执行命令，仅输出预览 |
| 执行日志 | `--execution-log-dir` 输出 `execution_log_<session>.jsonl` |
| 命令长度限制 | 默认 1024 字符 |
| unsafe 二次确认 | 需设置 `HARNESS_UNSAFE=1` 环境变量 |

#### 变更文件

- `harness_sdk/safety.py`：新增 `CommandSafetyChecker`、`SafetyConfig`、`SafetyResult`、`SafetyMode`
- `harness_sdk/executor.py`：`SubprocessExecutor` 集成安全校验、dry-run、日志落盘
- `harness_sdk/models.py`：`ExecutionResult` 新增 `blocked`、`dry_run`、`reason`
- `harness_sdk/runner.py`：透传 `session_id` 给 executor
- `harness_probe/cli.py`：`run` 新增 `--dry-run`、`--safety-mode`、`--execution-log-dir`
- `harness_mcp/tools.py`：`probe_run` 新增 `dry_run`、`safety_mode`、`execution_log_dir`
- `tests/test_sdk_executor.py`：旧真实执行测试显式使用 `safety_mode="unsafe"`
- `tests/test_sdk_safety.py`：新增安全校验覆盖测试
- `pyproject.toml`：`version = "0.7.0"`
- `README.md`、`CHANGELOG.md`：更新 v0.7 说明
- `docs/harness/tasks/active/task_harness_probe_phase5_safety_executor_v1.md`：回填实现备忘与自检结论
- `docs/harness/invokes/by-task/harness-probe-phase5-safety-executor-v1/INVOKE_20260630_30_v1.md`：invoke 快照

## 验证结果

| 检查项 | 结果 |
| --- | --- |
| `pytest tests/ -q` | **49 passed** |
| `ruff check harness_sdk tests harness_probe harness_mcp` | **All checks passed** |
| `mypy harness_sdk --ignore-missing-imports` | **Success** |
| CLI dry-run | `done` |
| CLI audit 模式 | `blocked` |
| `npx @cyning/harness verify` Phase 5 task | **VERIFY: PASS** |

## Git 状态

```text
a392da7 (HEAD -> main, tag: v0.7.0, origin/main, origin/HEAD) merge(phase5): ...
```

- `main` 已推送至 `origin/main`
- tag `v0.7.0` 已推送

## 经验教训

1. **Markdown 表格解析必须 normalize 格式化符号**：反引号、星号会改变解析结果，产品包与业务代码都应做防御性清洗。
2. **测试必须覆盖真实格式**：不要只测裸字符串，要覆盖 `` `approved` ``、`*approved*`、`` **`approved`** `` 等变体。
3. **awk 与 JS 正则差异**：awk 中 `` [`\*] `` 会报错，应写 `` [`*] ``；修改 shell 脚本后必须实际运行验证。
4. **安全执行器默认应收紧**：v0.7 将默认安全模式从 `unsafe` 改为 `whitelist`，旧测试需显式降级，避免真实执行时意外放行危险命令。
5. **执行日志是审计关键**：所有 executed / blocked / timeout / dry_run 事件统一落盘，便于 40 帽审计与事后追溯。

## 下一步建议

1. **Phase 6 规划**：可考虑将安全执行器扩展为可配置策略文件（YAML），支持项目级自定义白名单。
2. **CI 加固**：在 GitHub Actions 中增加 `--executor real --dry-run` 与 `--safety-mode audit` 的端到端测试。
3. **MCP 文档**：补充 MCP `probe_run` 新参数的示例。
4. **产品包回归测试**：在 `cyning-harness` 中增加对反引号 task 表的自动化测试，防止类似回归。

## 相关链接

- 任务单：`docs/harness/tasks/active/task_harness_probe_phase5_safety_executor_v1.md`
- invoke：`docs/harness/invokes/by-task/harness-probe-phase5-safety-executor-v1/INVOKE_20260630_30_v1.md`
- postmortem：`../cyning-harness/docs/methodology/execution/POSTMORTEM_backtick_gate_parsing_v1_zh.md`
- CHANGELOG：`CHANGELOG.md`
- README：`README.md`
