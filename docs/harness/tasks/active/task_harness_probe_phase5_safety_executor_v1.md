# task_harness_probe_phase5_safety_executor_v1

## 元信息

| 字段 | 值 |
| --- | --- |
| 状态 | `draft` |
| 目标版本 | v0.7 |
| 关联图谱 | `docs/_tech_graph/10_flow_verify.ai.md`（待更新） |
| 关联规划 | `docs/PLAN_PHASE5_v1_zh.md` |
| test_strategy | `required` |

## 人工闸

| 闸口 | 状态 | 说明 |
| --- | --- | --- |
| HG-TASK-DRAFT | `approved` | 本任务单定稿 |
| HG-AUDIT-R1 | `approved` | R1 书面审通过，允许改码 |
| HG-EXEC-AUTH | `approved` | 授权使用 Claude Code 执行 |

## 背景与目标

v0.6 已让 `probe_run` / `probe_audit` 支持真实执行 `contract.verify`，但执行器缺少安全边界。本任务目标是在不引入完整 sandbox 的前提下，为 `--executor real` 增加：

1. 命令白名单与危险字符/命令黑名单
2. `--dry-run` 预览模式
3. 独立执行日志落盘

## 范围

- `harness_sdk/safety.py`：新增 `CommandSafetyChecker`、`SafetyConfig`、`SafetyResult`
- `harness_sdk/executor.py`：`SubprocessExecutor` 集成 safety checker、dry-run、log sink
- `harness_sdk/models.py`：`ExecutionResult` 新增 `blocked`、`dry_run`、`reason` 字段
- `harness_probe/cli.py`：`run` 子命令新增 `--dry-run`、`--safety-mode`、`--execution-log-dir`
- `harness_mcp/tools.py`：`probe_run` 新增 `dry_run`、`safety_mode` 参数
- `config/probe_config.yaml`：新增 `executor.safety` 配置段（如不存在则创建）
- `tests/test_sdk_safety.py`：覆盖白名单/黑名单/dry-run/audit/unsafe 模式
- `tests/test_cli.py`：新增 CLI 端到端测试
- `README.md`、`CHANGELOG.md`：更新 v0.7 说明

## 非范围

- 不引入 Docker / seccomp / sandbox 隔离
- 不做命令语义级分析
- 不接入 LLM 自动修复
- 不改帽链语义、graph.json、task 单格式

## 依赖

- v0.6 已合并至 `main`
- `docs/PLAN_PHASE5_v1_zh.md` 已存在

## 验收标准

- [ ] `pytest tests/ -q` 全绿
- [ ] `ruff check harness_sdk tests harness_probe harness_mcp` 通过
- [ ] `mypy harness_sdk --ignore-missing-imports` 通过
- [ ] `--executor real` 默认启用白名单，危险命令被拦截
- [ ] `--dry-run` 不实际执行，输出预览
- [ ] 真实执行与拦截事件均写入 `outputs/execution_log_*.jsonl`
- [ ] MCP `probe_run` 支持 `dry_run` / `safety_mode`

## 失败路径

| ID | 触发条件 | 系统行为 | 可重试 | 用户可见 |
| --- | --- | --- | --- | --- |
| S1 | 危险 shell 元字符 | `returncode=-2`，`blocked=True` | 否 | CLI 报错 |
| S2 | 危险命令前缀 | `returncode=-2`，`blocked=True` | 否 | CLI 报错 |
| S3 | 不在白名单 | `returncode=-2`，`blocked=True` | 否 | 提示更新配置 |
| S4 | 命令超长 | `returncode=-2`，`blocked=True` | 否 | 提示缩短命令 |
| S5 | dry-run 模式 | 不执行，返回预览 | 是 | 输出命令列表 |
| S7 | unsafe 模式未二次确认 | 拒绝执行 | 否 | 提示环境变量 |

## 实现备忘

- 待 R1 批准后由子 Agent 回填

## 测试策略

`required`。安全执行属于关键路径，必须先有可失败的自动化测试覆盖白名单/黑名单/dry-run，再改实现。

## 修订记录

| 版本 | 日期 | 说明 |
| --- | --- | --- |
| v1 | 2026-06-30 | 初稿 |
