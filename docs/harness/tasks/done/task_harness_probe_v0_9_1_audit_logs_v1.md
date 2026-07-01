# task_harness_probe_v0_9_1_audit_logs_v1

## Harness 元信息

| 字段 | 值 |
| --- | --- |
| **track** | `feature` |
| **lightweight_task** | `no` |
| **module_id** | `AUDIT` |
| **graph_delta** | `docs/_tech_graph/85_audit.graph.yaml` |
| **freeze_id** | `v0.9.1` |
| **test_strategy** | `required` |
| **failure_paths** | 见下文 |

### 人工闸 `human_gate`

| human_gate_id | status | blocks_hats | 说明 |
| --- | --- | --- | --- |
| HG-TASK-DRAFT | `approved` | 30 | 任务单已定稿 |
| HG-AUDIT-R1 | `approved` | 30 | R1 审计通过：v0.9.1 日志审计独立且为后续配置/LLM 提供基础 |
| HG-EXEC-AUTH | `approved` | 30 | 已授权 30 改码，可派工 Claude Code |

## 背景与目标

v0.9.0 已完成 CI 集成。v0.9.1 目标是为 Harness Probe 引入完整的执行日志、审计与报告能力：
- 记录每次 `run` / `verify` / `compile` 的完整上下文
- 输出结构化 JSON / Markdown 报告
- 支持按 task、hat、时间、执行器插件维度查询
- 为 v0.9.2 配置继承与 v0.9.9 LLM 审计提供数据基础

## 范围

### 核心

- 新增 `harness_sdk/audit/`：
  - `logger.py`：`AuditLogger` 单例，记录事件到本地目录
  - `events.py`：`RunEvent`、`VerifyEvent`、`CompileEvent` 等事件模型
  - `report.py`：`AuditReport` 生成器，支持 JSON / Markdown
  - `reader.py`：按 task/hat/time/executor 维度查询历史日志
- 新增 `harness_probe/cli.py` 审计子命令：
  - `harness-probe audit list --task task.md --since 2026-06-01`
  - `harness-probe audit show --run-id <uuid>`
  - `harness-probe audit report --task task.md --format markdown --output report.md`
- 集成到现有命令：
  - `run`、`verify`、`compile` 默认写入审计日志（可通过 `--no-audit` 关闭）
- 新增 `config/audit.yaml`：
  - 日志目录
  - 保留策略（数量/天数）
  - 默认格式

### CLI/SDK

- 保持 public API 不变
- `ExecutionResult` 增加 `run_id` 字段（UUID）
- `AuditReport` 可导出为 JSON 或 Markdown

### 文档/图谱

- 新增 `docs/_tech_graph/85_audit.graph.yaml`：审计流程
- 重新导出 `graph.json` 和 `.md`
- 新增 `docs/examples/audit/README.md`：审计日志与报告示例
- 更新 `CHANGELOG.md`
- 更新 `pyproject.toml` 版本号为 `0.9.1`

## 非范围

- 多环境配置（v0.9.2）
- LLM 自动审计（v0.9.9）
- 远程审计日志存储（v1.0.0 后）
- 加密或签名审计日志（v1.0.0 后）

## 依赖与引用

- `docs/PLAN_v0_9_to_v1_zh.md`
- `harness_sdk/executor_plugins/`
- `harness_probe/cli.py`
- `harness_probe/ci.py`
- `config/audit.yaml`（新增）

## 验收标准

- [ ] `harness-probe run task.md` 后日志目录生成事件文件
- [ ] `harness-probe audit list` 能列出历史运行
- [ ] `harness-probe audit show --run-id <id>` 能显示单次运行详情
- [ ] `harness-probe audit report` 能生成 JSON 和 Markdown 报告
- [ ] 日志包含：task 路径、hat、执行器插件、命令、结果、时间戳、运行时长
- [ ] 日志保留策略生效（超过数量/天数自动清理）
- [ ] `--no-audit` 可禁用日志写入
- [ ] `pytest tests/ -q` 全绿
- [ ] `ruff check .` 全绿
- [ ] `mypy harness_sdk` 全绿
- [ ] 图谱与 CHANGELOG 同步更新
- [ ] 创建并推送 `task/v0-9-1-audit-logs` 分支

## 实现备忘

- 待执行后回填

## 测试策略

`required`。审计是 Harness 安全与可追溯性的核心，必须有可失败测试覆盖事件写入、查询、报告和保留策略。

## 失败路径

| 触发条件 | 系统行为 | 是否可重试 | 用户可见类型 |
| --- | --- | --- | --- |
| 日志目录不可写 | 降级为内存日志，发出警告 | 修复目录权限后重试 | 警告 |
| 日志文件损坏 | 跳过该条，记录到 `.audit/errors` | 不可恢复 | 警告 |
| 保留策略清理失败 | 下次运行时重试清理 | 手动删除 | 警告 |
| `--run-id` 不存在 | `audit show` 返回错误码 1 | 修正 id 后重试 | 错误提示 |

## 给 Cursor

- 只修改必要文件：`harness_sdk/audit/`、CLI 审计子命令、测试、文档
- 保持 v0.9.0 的 CI/workflow 与执行器接口不变
- 不要直接提交到 main，创建分支并推送
- 审计日志默认保存在 `~/.harness_probe/audit/` 或项目 `.harness/audit/`
