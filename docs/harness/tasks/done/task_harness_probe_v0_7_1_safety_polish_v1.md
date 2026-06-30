# task_harness_probe_v0_7_1_safety_polish_v1

## Harness 元信息

| 字段 | 值 |
| --- | --- |
| **track** | `feature` |
| **lightweight_task** | `yes` |
| **module_id** | `SAFETY` |
| **graph_delta** | `docs/_tech_graph/90_executor.graph.yaml` |
| **freeze_id** | `v0.7.0` |
| **test_strategy** | `required` |
| **failure_paths** | 见下文 |

### 人工闸 `human_gate`

| human_gate_id | status | blocks_hats | 说明 |
| --- | --- | --- | --- |
| HG-TASK-DRAFT | `approved` | 30 | 任务单定稿 |
| HG-AUDIT-R1 | `approved` | 30 | 轻量补丁，跳过 R1 审计 |
| HG-EXEC-AUTH | `approved` | 30 | 授权执行 30 改码 |

## 背景与目标

v0.7.0 已引入 `CommandSafetyChecker` 与 `SafetyMode`（whitelist/audit/unsafe），但配置只能通过代码或 CLI 参数传入。v0.7.1 的目标是让安全策略可项目化、错误信息更可读，并补齐 CLI/MCP 的端到端测试。

## 范围

- 实现 `config/safety.yaml` 加载与合并
- 增强 `blocked` 时的错误信息
- 新增 `test_cli_safety.py` 与 `test_mcp_safety.py`
- 更新 `docs/_tech_graph/90_executor.graph.yaml` 与 `README.md` FAQ

## 非范围

- 策略热重载（v0.8.0）
- 沙箱预览（v0.8.0）
- 执行器插件化（v0.8.0）
- CI Action（v0.8.0）

## 依赖与引用

- `docs/PLAN_v0_7_x_zh.md`
- `harness_sdk/safety.py`
- `harness_sdk/executor.py`
- `harness_probe/cli.py`
- `harness_mcp/tools.py`

## 验收标准

- [x] `config/safety.yaml` 可被 `--safety-config` 加载
- [x] 项目级白名单扩展默认白名单，危险前缀不可被覆盖
- [x] `blocked` 时返回明确原因与操作建议
- [x] 新增 CLI 安全测试 ≥ 3 个
- [x] 新增 MCP 安全测试 ≥ 3 个
- [x] `pytest tests/ -q` 全绿
- [x] `ruff check harness_sdk tests harness_probe harness_mcp` 全绿
- [x] `mypy harness_sdk --ignore-missing-imports` 全绿
- [x] 图谱与 README 同步更新

## 实现备忘

- 已合并到 `main`（commit `4502e59`）
- 新增文件：`config/safety.yaml`、`examples/safety/README.md`、`tests/test_cli_safety.py`、`tests/test_mcp_tools_safety.py`
- 修改文件：`harness_sdk/safety.py`、`harness_sdk/executor.py`、`harness_sdk/runner.py`、`harness_probe/cli.py`、`harness_probe/io.py`、`harness_mcp/tools.py`、`pyproject.toml`、`CHANGELOG.md`、`docs/_tech_graph/90_executor.graph.yaml`
- 验证：pytest 61 passed, ruff passed, mypy passed, graph-query OK, verify OK
- 状态：关闭并归档到 `docs/harness/tasks/done/`

## 测试策略

`required`。安全执行器是关键路径，新增配置与错误提示必须有可失败测试。

## 失败路径

| 触发条件 | 系统行为 | 是否可重试 | 用户可见类型 |
| --- | --- | --- | --- |
| `config/safety.yaml` 不存在 | 回退到默认 `SafetyConfig` | 否 | 警告日志 |
| `config/safety.yaml` YAML 解析失败 | 抛出 `SafetyConfigError`，CLI 退出码 1 | 修复文件后重试 | 错误信息 |
| 项目配置尝试覆盖危险前缀 | 忽略危险前缀覆盖，打印警告 | 否 | 警告日志 |
| 命令被 whitelist 拦截 | `ExecutionResult.blocked=True`，原因 `not_in_whitelist` | 更新配置或改用 audit | 明确提示 |
| 命令含危险字符 | `ExecutionResult.blocked=True`，原因 `dangerous_metacharacter` | 不可重试 | 明确提示 |

## 给 Cursor

- 只修改 `harness_sdk/safety.py`、`harness_probe/cli.py`、`harness_mcp/tools.py`、测试、文档
- 保持 v0.7.0 CLI/MCP 接口向后兼容
- 新增配置字段需同步 `SafetyConfig` dataclass
