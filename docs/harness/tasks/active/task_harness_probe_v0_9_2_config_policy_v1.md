# task_harness_probe_v0_9_2_config_policy_v1

## Harness 元信息

| 字段 | 值 |
| --- | --- |
| **track** | `feature` |
| **lightweight_task** | `no` |
| **module_id** | `CONFIG` |
| **graph_delta** | `docs/_tech_graph/95_config.graph.yaml` |
| **test_strategy** | `required` |
| **failure_paths** | 见下方 |
| **freeze_id** | `v0.9.5` |
| **parent_id** | `v0.9.1` |
| **risk** | `low` |

## 人工闸

| 闸 | 状态 | 阻塞 hat | 说明 |
| --- | --- | --- | --- |
| HG-TASK-DRAFT | `approved` | 30 | 任务单已定稿 |
| HG-AUDIT-R1 | `approved` | 30 | R1 审计通过：v0.9.2 配置中心与策略增强范围清晰 |
| HG-EXEC-AUTH | `approved` | 30 | 已授权 30 改码，可派工 Claude Code |

## 背景与目标

v0.8.x 引入执行器插件与沙箱、v0.9.0 引入 CI、v0.9.1 引入审计。当前配置散落为 `config/executor.yaml`、`config/audit.yaml`、`config/safety.yaml`，存在加载方式不统一、环境变量覆盖不一致、缺少集中校验的问题。

v0.9.2 目标：建立**配置中心（Config Manager）**与**策略增强**，统一配置加载、合并、校验与热重载。

## 范围

### 在范围内

- 新建 `harness_sdk/config.py` 配置中心：
  - 统一加载 `config/*.yaml`
  - 支持环境变量覆盖（`HARNESS_*` 前缀）
  - 支持按优先级合并：默认值 < 配置文件 < 环境变量 < 命令行参数
  - 提供配置校验（schema/类型检查）与友好错误提示
- 重构现有配置使用点：
  - `executor.py` / `executor_plugins/_loader.py` 使用统一配置
  - `audit/logger.py` 使用统一配置
  - `safety.py` 使用统一配置（保留 reload 能力）
- 新增 CLI 子命令：`harness-probe config validate` 与 `harness-probe config show`
- 新增配置图谱 `docs/_tech_graph/95_config.graph.yaml`
- 新增 `docs/examples/config/README.md`
- 测试覆盖：配置合并、环境变量覆盖、校验错误、CLI 输出
- 更新 CHANGELOG 与 `pyproject.toml` 版本号到 `0.9.2`

### 非范围

- 不引入新的执行器插件或沙箱
- 不接入真实 LLM
- 不改 cyning-harness product repo
- 不做 UI/Web 配置界面

## 依赖与引用

- `harness_sdk/executor_plugins/_loader.py`
- `harness_sdk/audit/logger.py`
- `harness_sdk/safety.py`
- `docs/_tech_graph/90_executor.graph.yaml`
- `docs/_tech_graph/85_audit.graph.yaml`
- `docs/_tech_graph/80_ci.graph.yaml`

## 验收标准

- [ ] `harness_sdk/config.py` 实现配置中心
- [ ] `config/*.yaml` 可被统一加载，环境变量覆盖生效
- [ ] `harness-probe config validate` 能检查配置并返回正确退出码
- [ ] `harness-probe config show` 能输出当前合并后的配置（JSON/Markdown）
- [ ] 执行器、审计、安全模块通过配置中心读取配置，CLI 行为一致
- [ ] 配置错误时给出明确错误信息，不抛堆栈
- [ ] `pytest tests/ -q` 全绿
- [ ] `ruff check .` 全绿
- [ ] `mypy harness_sdk` 全绿
- [ ] 图谱与 CHANGELOG 同步更新
- [ ] 创建并推送 `task/v0-9-2-config-policy` 分支

## 失败路径

| 触发条件 | 系统行为 | 用户可见 | 可重试 |
| --- | --- | --- | --- |
| 配置文件不存在 | 使用内置默认值，发出警告 | 警告信息 | 是 |
| YAML 格式损坏 | 捕获异常，退出码 2，提示文件路径 | 明确错误 | 是 |
| 配置值类型错误（如 timeout 为字符串） | 校验失败，退出码 2 | 字段名 + 期望类型 | 是 |
| 环境变量覆盖为非法值 | 校验失败，退出码 2 | 变量名 + 原因 | 是 |

## 实现备忘

- 待执行后回填文件列表、接口变更、图谱更新点
