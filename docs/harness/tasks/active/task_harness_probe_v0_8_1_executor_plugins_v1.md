# task_harness_probe_v0_8_1_executor_plugins_v1

## Harness 元信息

| 字段 | 值 |
| --- | --- |
| **track** | `feature` |
| **lightweight_task** | `no` |
| **module_id** | `EXECUTOR` |
| **graph_delta** | `docs/_tech_graph/90_executor.graph.yaml` |
| **freeze_id** | `v0.8.1` |
| **test_strategy** | `required` |
| **failure_paths** | 见下文 |

### 人工闸 `human_gate`

| human_gate_id | status | blocks_hats | 说明 |
| --- | --- | --- | --- |
| HG-TASK-DRAFT | `approved` | 30 | 任务单已定稿 |
| HG-AUDIT-R1 | `approved` | 30 | R1 审计通过：v0.8.1 是 v0.9.0 和 v0.8.2 的前置依赖，范围清晰 |
| HG-EXEC-AUTH | `approved` | 30 | 已授权 30 改码，可派工 Claude Code |

## 背景与目标

v0.8.0 已完成沙箱预览与策略热重载。v0.8.1 目标是把当前硬编码的 `SubprocessExecutor` 抽象为插件体系，使 `dry-run` / `preview` / `real` 三种执行模式都通过统一 `VerifyExecutor` 协议运行。这是 v0.9.0 CI 集成和 v0.8.2 沙箱原型的前置依赖。

## 范围

### 核心

- 定义 `VerifyExecutor` 协议：
  - `async run(cmd, cwd, session_id) -> ExecutionResult`
  - `supports(cmd) -> bool`
  - `describe() -> str`
- 把 `SubprocessExecutor` 迁移为 `harness_sdk/executor_plugins/subprocess.py` 的默认插件
- 新增 `DryRunExecutor`（原 mock 行为）
- 新增 `PreviewExecutor`（不执行命令，返回 `PreviewReport`）
- 新增插件加载工厂：`load_executor_plugin(name)`

### CLI/SDK

- `harness_probe/cli.py`：`--executor` 参数保持 `mock`/`real` 向后兼容，同时支持 `--executor-plugin` 选择插件名
- `harness_sdk/executor.py`：保留兼容层导出，避免破坏外部导入
- `config/executor.yaml`：默认执行器配置

### 文档/图谱

- 更新 `docs/_tech_graph/90_executor.graph.yaml` 反映插件结构
- 重新导出 `graph.json` 和 `.md`
- 更新 `CHANGELOG.md`
- 更新 `pyproject.toml` 版本号为 `0.8.1`

## 非范围

- Docker / Firejail 沙箱（v0.8.2）
- LLM Provider（v0.9.9）
- CI Action（v0.9.0）
- 日志审计（v0.9.1）
- 多环境配置（v0.9.2）

## 依赖与引用

- `docs/PLAN_v0_8_x_zh.md`
- `docs/PLAN_v0_9_0_zh.md`（依赖插件化接口）
- `harness_sdk/executor.py`
- `harness_sdk/safety.py`
- `harness_probe/cli.py`
- `harness_mcp/tools.py`

## 验收标准

- [x] `VerifyExecutor` 协议定义清晰
- [x] `DryRunExecutor`、`PreviewExecutor`、`SubprocessExecutor` 都通过统一接口运行
- [x] CLI `--executor mock`/`real` 行为与 v0.8.0 一致
- [x] CLI `--executor-plugin dry-run` / `preview` / `subprocess` 可切换
- [x] `config/executor.yaml` 可配置默认插件
- [x] `pytest tests/ -q` 全绿
- [x] `ruff check .` 全绿
- [x] `mypy harness_sdk` 全绿
- [x] 图谱与 CHANGELOG 同步更新
- [x] 创建并推送 `task/v0-8-1-executor-plugins` 分支

## 实现备忘

- 已实现并提交到分支 `task/v0-8-1-executor-plugins`
- 新增：`harness_sdk/executor_plugins/`（base, dry_run, preview, subprocess, _loader）
- 新增：`config/executor.yaml`、`tests/test_executor_plugins.py`
- 修改：`harness_sdk/executor.py`（兼容层）、`harness_probe/cli.py`（--executor-plugin 参数）、`CHANGELOG.md`、`pyproject.toml`、图谱
- 验证：pytest 85 passed, ruff passed, mypy passed
- 状态：待合并到 main，关闭并归档到 `docs/harness/tasks/done/`

## 测试策略

`required`。执行器是 Harness 核心路径，插件化重构必须有可失败测试覆盖行为一致性。

## 失败路径

| 触发条件 | 系统行为 | 是否可重试 | 用户可见类型 |
| --- | --- | --- | --- |
| 指定未知插件名 | 抛出 `ExecutorPluginError`，CLI 退出码 2 | 修正后重试 | 错误提示 |
| 插件 `supports()` 返回 False | 回退到默认 `SubprocessExecutor` 或 blocked | 是 | 警告 |
| 配置文件插件名错误 | 加载失败，回退默认 | 修正配置后重试 | 错误提示 |
| `SubprocessExecutor` 被移除 | 保留兼容导入，避免外部代码 break | 否 | 弃用警告 |

## 给 Cursor

- 只修改 `harness_sdk/executor.py`、`harness_sdk/executor_plugins/`、CLI、测试、文档
- 保持 `--executor mock` 和 `--executor real` 行为不变
- 保持 `SubprocessExecutor` 可通过 `harness_sdk.executor` 导入
- 新增插件目录结构要清晰，不要过度抽象
- 修改后优先运行 `pytest tests/ -q`
