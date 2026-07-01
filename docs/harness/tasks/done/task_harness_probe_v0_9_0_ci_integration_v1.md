# task_harness_probe_v0_9_0_ci_integration_v1

## Harness 元信息

| 字段 | 值 |
| --- | --- |
| **track** | `feature` |
| **lightweight_task** | `no` |
| **module_id** | `CI` |
| **graph_delta** | `docs/_tech_graph/80_ci.graph.yaml` |
| **freeze_id** | `v0.9.0` |
| **test_strategy** | `required` |
| **failure_paths** | 见下文 |

### 人工闸 `human_gate`

| human_gate_id | status | blocks_hats | 说明 |
| --- | --- | --- | --- |
| HG-TASK-DRAFT | `approved` | 30 | 任务单已定稿 |
| HG-AUDIT-R1 | `approved` | 30 | R1 审计通过：v0.9.0 CI 集成依赖 v0.8.x 插件体系，范围清晰 |
| HG-EXEC-AUTH | `approved` | 30 | 已授权 30 改码，可派工 Claude Code |

## 背景与目标

v0.8.2 已完成沙箱执行器原型。v0.9.0 目标是为 Harness Probe 提供 GitHub Actions 集成，使任务单验证可以在 CI 中复用。包括：
- GitHub Action 复用工作流
- 本地 action 验证工具
- 与 v0.8.1 插件体系对接，在 CI 中切换 dry-run/preview/real/sandbox 执行器

## 范围

### 核心

- 新增 `.github/workflows/harness.yml`：
  - 支持矩阵 OS（ubuntu-latest, macos-latest）
  - 安装 Python 依赖
  - 运行 `pytest tests/ -q`
  - 运行 `ruff check .` 和 `mypy harness_sdk`
  - 可选运行沙箱测试（Docker on Linux）
- 新增 `.github/actions/harness-run/action.yml`：
  - 可复用 action，接收参数：
    - `task`
    - `hat`
    - `executor-plugin`
    - `safety-config`
    - `preview`
  - 输出 `ExecutionResult` 的 JSON
- 新增 `harness_probe/ci.py`：
  - 生成 GitHub Actions workflow 片段
  - 本地验证 action 输入
- 新增 `tests/test_ci_integration.py`：
  - 验证 action.yml 解析
  - 验证 workflow 生成
  - 验证 CI 环境下的执行器选择

### CLI/SDK

- `harness_probe/cli.py` 新增 `ci` 子命令：
  - `harness-probe ci generate --task task.md --os ubuntu-latest --executor-plugin dry-run`
  - `harness-probe ci validate --workflow .github/workflows/harness.yml`

### 文档/图谱

- 新增 `docs/_tech_graph/80_ci.graph.yaml`：CI 集成流程
- 重新导出 `graph.json` 和 `.md`
- 新增 `docs/examples/ci/README.md`：GitHub Actions 使用示例
- 更新 `CHANGELOG.md`
- 更新 `pyproject.toml` 版本号为 `0.9.0`

## 非范围

- 日志审计增强（v0.9.1）
- 多环境配置（v0.9.2）
- LLM Provider（v0.9.9）
- 沙箱网络/存储复杂策略（v1.0.0 后）
- 其他 CI 平台（GitLab CI、CircleCI 等，v1.0.0 后）

## 依赖与引用

- `docs/PLAN_v0_9_0_zh.md`
- `docs/PLAN_v0_9_to_v1_zh.md`
- `harness_sdk/executor_plugins/`
- `harness_probe/cli.py`
- `config/executor.yaml`

## 验收标准

- [ ] `.github/workflows/harness.yml` 可运行 pytest/ruff/mypy
- [ ] `.github/actions/harness-run/action.yml` 参数解析正确
- [ ] `harness-probe ci generate` 可生成 workflow 片段
- [ ] `harness-probe ci validate` 可验证 workflow 文件
- [ ] CI 中可切换 `dry-run`/`preview`/`subprocess`/`docker` 执行器
- [ ] Docker 沙箱测试仅在 Linux CI 上可选运行
- [ ] `pytest tests/ -q` 全绿
- [ ] `ruff check .` 全绿
- [ ] `mypy harness_sdk` 全绿
- [ ] 图谱与 CHANGELOG 同步更新
- [ ] 创建并推送 `task/v0-9-0-ci-integration` 分支

## 实现备忘

- 待执行后回填

## 测试策略

`required`。CI 集成是 Harness 生产化的关键路径，必须有可失败测试覆盖 action 解析和 workflow 生成。

## 失败路径

| 触发条件 | 系统行为 | 是否可重试 | 用户可见类型 |
| --- | --- | --- | --- |
| workflow 文件格式错误 | `validate` 子命令返回错误码 1 | 修正后重试 | 错误提示 |
| action 输入参数缺失 | 解析失败，提示必填参数 | 修正后重试 | 错误提示 |
| CI 中执行器不可用 | 降级到 dry-run 或报错 | 修正配置后重试 | 警告/错误 |
| CI 环境无 Docker | 跳过 Docker 沙箱测试 | 使用 Linux runner 重试 | 警告 |

## 给 Cursor

- 只修改必要文件：`.github/workflows/`、`.github/actions/`、`harness_probe/cli.py`、新增 `harness_probe/ci.py`、测试、文档
- 保持 v0.8.2 插件接口不变
- 不要直接提交到 main，创建分支并推送
- 确保 CI workflow 在 GitHub 上能运行（至少 ubuntu-latest）
