# task_harness_probe_v0_9_3_audit_regression_fix

## Harness 元信息

| 字段 | 值 |
| --- | --- |
| **track** | `hotfix` |
| **lightweight_task** | `no` |
| **module_id** | `AUDIT` |
| **graph_delta** | `docs/_tech_graph/85_audit.graph.yaml` |
| **freeze_id** | `v0.9.3` |
| **test_strategy** | `required` |
| **failure_paths** | 见下文 |

### 人工闸 `human_gate`

| human_gate_id | status | blocks_hats | 说明 |
| --- | --- | --- | --- |
| HG-TASK-DRAFT | `approved` | 30 | 任务单已定稿 |
| HG-AUDIT-R1 | `approved` | 30 | R1 审计通过：回归必须有可失败测试覆盖 |
| HG-EXEC-AUTH | `approved` | 30 | 已授权 30 改码，可派工 Claude Code |

## 背景与目标

v0.9.2 合并后，`harness_sdk/audit/` 仅剩下 `logger.py`，导致：
- `RunEvent` / `VerifyEvent` / `CompileEvent` 丢失
- `AuditReader` / `AuditReport` 丢失
- `harness-probe audit` 子命令丢失
- v0.9.1 的 15 个审计测试失败

本任务修复上述回归，将审计能力重新整合到 v0.9.2 配置中心架构中，并升级到 v0.9.3。

## 范围

### 核心

- 恢复 v0.9.1 审计文件：`harness_sdk/audit/__init__.py`、`events.py`、`reader.py`、`report.py`、`retention.py`
- 调整 `harness_sdk/audit/logger.py`：
  - 读取 `HARNESS_AUDIT_LOG_DIR` 环境变量与 `harness.audit.log_dir` 配置
  - 兼容直接传入 audit 段字典（测试用例）与 `ConfigManager`
  - 保持单例、内存回退、保留策略
- 调整 `harness_sdk/audit/reader.py`：默认 log_dir 也统一读取环境变量/配置
- 恢复 `harness_probe/cli.py` 审计功能：
  - `run` / `verify` / `compile` 的 `--no-audit` 开关
  - `audit list` / `show` / `report` / `config` 子命令
- 恢复测试：`tests/test_audit_logger.py`、`test_audit_reader.py`、`test_audit_report.py`、`test_cli_audit.py`
- 更新 `CHANGELOG.md` 与 `pyproject.toml` 版本到 `0.9.3`

### 非范围

- 不新增审计事件类型
- 不改 audit 安全模型（加密、签名等）
- 不改动 v0.9.2 配置中心核心逻辑

## 依赖与引用

- `docs/PLAN_v0_9_to_v1_zh.md`
- `docs/harness/tasks/done/task_harness_probe_v0_9_1_audit_logs_v1.md`
- `harness_sdk/config.py`
- `harness_sdk/audit/`
- `harness_probe/cli.py`
- `config/audit.yaml`

## 验收标准

- [x] `harness_sdk/audit/` 目录完整恢复
- [x] `harness-probe audit list` 能列出历史运行
- [x] `harness-probe audit show --run-id <id>` 能显示单次运行详情
- [x] `harness-probe audit report` 能生成 JSON 和 Markdown 报告
- [x] `run` / `verify` / `compile` 默认写入审计日志，`--no-audit` 可关闭
- [x] `pytest tests/ -q` 全绿（147 passed, 4 skipped）
- [x] `ruff check .` 全绿
- [x] `mypy harness_sdk` 全绿
- [x] `CHANGELOG.md` 与版本号同步更新
- [x] 创建并推送 `task/v0-9-3-audit-regression-fix` 分支，合并到 `main`

## 实现备忘

- 已恢复：`harness_sdk/audit/__init__.py`、`events.py`、`reader.py`、`report.py`、`retention.py`
- 已重写 `harness_probe/cli.py` 审计相关部分，兼容 v0.9.2 `TaskRunner` 接口（`get_last_prompts()`、`planned_hats`）
- 已调整 `AuditReader._default_log_dir()` 与 `AuditLogger` 使用相同的 `_resolve_log_dir(config)` 路径解析，确保 CLI 和 SDK 读取同一日志目录
- 已修复 `AuditReport` 的 `hat` 过滤与 `AuditReader.list_runs` 签名
- 已提交合并：`task/v0-9-3-audit-regression-fix` → `main`

## 测试策略

`required`。审计是 Harness 安全与可追溯性核心，必须有测试覆盖事件写入、查询、报告和 CLI 集成。

## 失败路径

| 触发条件 | 系统行为 | 是否可重试 | 用户可见类型 |
| --- | --- | --- | --- |
| 日志目录不可写 | 降级为内存日志，发出警告 | 修复目录权限后重试 | 警告 |
| 日志文件损坏 | 跳过该条，记录到 `.audit/errors` | 不可恢复 | 警告 |
| `--run-id` 不存在 | `audit show` 返回错误码 1 | 修正 id 后重试 | 错误提示 |
| 环境变量与配置冲突 | 环境变量优先 | 调整环境变量 | 配置说明 |

## 给 Cursor

- 只修改审计回归相关文件，不动 v0.9.2 配置中心核心
- 保持 `AuditLogger` 单例与配置兼容
- 不要直接提交到 main，创建分支并推送
- 所有测试必须真实通过

