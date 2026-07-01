# task_harness_probe_v0_8_2_sandbox_executor_v1

## Harness 元信息

| 字段 | 值 |
| --- | --- |
| **track** | `feature` |
| **lightweight_task** | `no` |
| **module_id** | `EXECUTOR` |
| **graph_delta** | `docs/_tech_graph/90_executor.graph.yaml` |
| **freeze_id** | `v0.8.2` |
| **test_strategy** | `required` |
| **failure_paths** | 见下文 |

### 人工闸 `human_gate`

| human_gate_id | status | blocks_hats | 说明 |
| --- | --- | --- | --- |
| HG-TASK-DRAFT | `approved` | 30 | 任务单已定稿 |
| HG-AUDIT-R1 | `approved` | 30 | R1 审计通过：v0.8.2 依赖 v0.8.1 插件体系，范围清晰 |
| HG-EXEC-AUTH | `approved` | 30 | 已授权 30 改码，可派工 Claude Code |

## 背景与目标

v0.8.1 已完成执行器插件化。v0.8.2 目标是在插件体系基础上引入沙箱执行器，使 Harness Probe 的真实执行具备隔离能力。默认不启用，需要显式指定。

## 范围

### 核心

- 新增 `harness_sdk/executor_plugins/sandbox.py`：
  - `SandboxExecutor` 抽象基类，继承 `VerifyExecutor`
  - 通用沙箱参数：image、timeout、network、memory、cpu
- 新增 `harness_sdk/executor_plugins/docker.py`：
  - `DockerExecutor`：在临时容器内执行命令
  - 限制网络、CPU、内存
  - 超时与容器资源回收
- 新增 `harness_sdk/executor_plugins/firejail.py`（可选，Linux only）：
  - `FirejailExecutor`：利用 firejail 做 Linux 沙箱
  - macOS 无 firejail 时友好降级到 Docker 或明确报错
- 更新 `harness_sdk/executor_plugins/_loader.py`：支持加载 docker/firejail 插件

### CLI/SDK

- `harness_probe/cli.py`：
  - `--executor-plugin docker` 支持
  - 沙箱参数：`--sandbox-image`、`--sandbox-timeout`、`--sandbox-no-network`、`--sandbox-memory`
- `config/executor.yaml`：
  - 注册 docker / firejail 插件
  - 沙箱默认配置

### 测试

- 新增 `tests/test_sandbox_executor.py`：
  - Docker 沙箱能执行简单命令
  - Firejail 在 Linux 上可用（标记为 optional/linux only）
  - 沙箱参数解析正确
  - 沙箱失败时返回明确错误
- 沙箱测试标记为慢测试/可选，默认不破坏 `pytest tests/ -q`

### 文档/图谱

- 更新 `docs/_tech_graph/90_executor.graph.yaml` 反映沙箱执行器
- 重新导出 `graph.json` 和 `.md`
- 更新 `CHANGELOG.md`
- 更新 `pyproject.toml` 版本号为 `0.8.2`
- 新增 `docs/examples/sandbox/README.md` 使用示例

## 非范围

- LLM Provider（v0.9.9）
- CI Action（v0.9.0）
- 日志审计增强（v0.9.1）
- 多环境配置（v0.9.2）
- 沙箱的网络/存储复杂策略（v1.0.0 后）

## 依赖与引用

- `docs/PLAN_v0_8_x_zh.md`
- `docs/PLAN_v0_9_0_zh.md`
- `harness_sdk/executor_plugins/`
- `harness_sdk/executor.py`
- `harness_probe/cli.py`

## 验收标准

- [ ] `DockerExecutor` 能执行简单命令并返回结果
- [ ] `FirejailExecutor` 在 Linux 上可用
- [ ] macOS 无 firejail 时有明确降级提示
- [ ] CLI `--executor-plugin docker` 可切换
- [ ] 沙箱参数正确透传给执行器
- [ ] 沙箱测试标记为可选/慢测试，不破坏默认套件
- [ ] `pytest tests/ -q` 全绿（默认不跑沙箱测试）
- [ ] `ruff check .` 全绿
- [ ] `mypy harness_sdk` 全绿
- [ ] 图谱与 CHANGELOG 同步更新
- [ ] 创建并推送 `task/v0-8-2-sandbox-executor` 分支

## 实现备忘

- 待执行后回填

## 测试策略

`required`。沙箱执行器是安全关键路径，但 Docker 环境不是 everywhere，因此默认测试套件跳过沙箱测试，但核心行为必须有可失败测试。

## 失败路径

| 触发条件 | 系统行为 | 是否可重试 | 用户可见类型 |
| --- | --- | --- | --- |
| Docker 未安装 | 明确报错，提示安装 Docker | 安装后重试 | 错误提示 |
| Firejail 未安装 | 在 Linux 上提示安装；macOS 降级到 Docker | 安装后重试 | 错误/警告 |
| 容器超时 | 返回 `ExecutionResult.timed_out=True` | 可调整 timeout 重试 | 错误提示 |
| 容器退出码非 0 | 返回 `ExecutionResult.returncode` | 视业务可重试 | 错误提示 |
| 沙箱参数非法 | 初始化失败，抛出 `SandboxConfigError` | 修正参数后重试 | 错误提示 |

## 给 Cursor

- 只修改 `harness_sdk/executor_plugins/`、`harness_probe/cli.py`、测试、文档
- 保持 v0.8.1 插件接口不变
- 沙箱默认不启用，不要强制安装 Docker
- 测试用 `pytest.mark` 标记为可选
- 不要直接提交到 main，创建分支并推送
