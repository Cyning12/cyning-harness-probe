# task_harness_probe_v0_8_0_sandbox_preview_v1

## Harness 元信息

| 字段 | 值 |
| --- | --- |
| **track** | `feature` |
| **lightweight_task** | `no` |
| **module_id** | `SAFETY` |
| **graph_delta** | `docs/_tech_graph/90_executor.graph.yaml` |
| **freeze_id** | `v0.8.0` |
| **test_strategy** | `required` |
| **failure_paths** | 见下文 |

### 人工闸 `human_gate`

| human_gate_id | status | blocks_hats | 说明 |
| --- | --- | --- | --- |
| HG-TASK-DRAFT | `approved` | 30 | 任务单已定稿 |
| HG-AUDIT-R1 | `in_progress` | 30 | 功能版 R1 审计中 |
| HG-EXEC-AUTH | `pending` | 30 | 待审计通过后授权 30 改码 |

## 背景与目标

v0.7.1 已完成安全策略文件化（`config/safety.yaml`）。v0.8.0 目标是在此基础上引入：

1. **策略热重载**：安全白名单/黑名单支持运行时更新
2. **沙箱预览**：真实执行前生成命令影响报告，包含命中规则、建议模式、风险等级

## 范围

### 8.1 · 策略热重载

- `SafetyConfig` 支持从 `config/safety.yaml` 加载（v0.7.1 已有，本任务增强运行时重载）
- CLI 新增 `--safety-reload` 参数
- 可选：文件变更时通过 `watchdog` 自动重载（作为可选依赖）
- 策略合并规则：项目配置扩展默认配置，危险前缀不可覆盖

### 8.2 · 沙箱预览

- 新增 `--preview` 模式：不执行命令，输出结构化影响报告
  - 命令解析结果
  - 命中的白名单/黑名单规则
  - 建议的安全模式
  - 风险等级（low/medium/high）
- `probe_run` 新增 `preview=True` 参数
- 输出格式：JSON / Markdown

## 非范围

- 执行器插件化（v0.8.1 或 v0.9.0）
- CI Action（v0.8.1 或 v0.9.0）
- 执行日志分析（v0.8.1 或 v0.9.0）
- 安全报告导出（v0.8.2 或 v0.9.0）
- 沙箱真实隔离（Docker / firejail，v0.9.0）

## 依赖与引用

- `docs/PLAN_v0_8_zh.md`
- `harness_sdk/safety.py`
- `harness_sdk/executor.py`
- `harness_probe/cli.py`
- `harness_mcp/tools.py`
- `docs/_tech_graph/90_executor.graph.yaml`

## 验收标准

- [ ] 8.1: `SafetyConfig` 支持显式 `reload()` 方法
- [ ] 8.1: CLI `--safety-reload` 在 `run` 前重新加载配置
- [ ] 8.1: 配置重载后新白名单/黑名单生效，并通过测试
- [ ] 8.2: `--preview` 输出结构化 JSON 报告
- [ ] 8.2: `probe_run` 支持 `preview=True` 参数
- [ ] 8.2: 风险等级计算规则可测试（白名单=low，黑名单=high，其他=medium）
- [ ] 8.2: 预览模式不执行任何命令
- [ ] `pytest tests/ -q` 全绿
- [ ] `ruff check .` 全绿
- [ ] `mypy harness_sdk` 全绿
- [ ] 图谱与 CHANGELOG 同步更新

## 实现备忘

- 待执行后回填

## 测试策略

`required`。安全执行器与沙箱预览是关键路径，必须有可失败自动化测试。

## 失败路径

| 触发条件 | 系统行为 | 是否可重试 | 用户可见类型 |
| --- | --- | --- | --- |
| `config/safety.yaml` 在运行时损坏 | 保留上一次有效配置，发出错误日志 | 修复文件后 `--safety-reload` 可重试 | 错误信息 |
| 预览模式遇到未知命令 | 风险等级 medium，建议 audit 模式 | 是 | 提示 |
| 预览模式命中黑名单 | 风险等级 high，建议 blocked | 否 | 明确提示 |
| `--preview` 与 `--executor real` 同时指定 | 优先 preview，不执行命令 | 是 | 警告提示 |

## 给 Cursor

- 只修改 `harness_sdk/safety.py`、`harness_sdk/executor.py`、`harness_probe/cli.py`、`harness_mcp/tools.py`、测试、文档
- 保持 v0.7.x 接口向后兼容（`--safety-config`、`--safety-mode` 行为不变）
- 新增预览报告结构需同步 `ExecutionResult` 或新增 `PreviewReport` dataclass
- 可选 `watchdog` 依赖，不要强制安装
