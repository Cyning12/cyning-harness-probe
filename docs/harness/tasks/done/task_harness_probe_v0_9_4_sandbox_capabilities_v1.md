# task_harness_probe_v0_9_4_sandbox_capabilities_v1

## Harness 元信息

| 字段 | 值 |
| --- | --- |
| **track** | `feature` |
| **lightweight_task** | `no` |
| **module_id** | `SAFETY` / `EXECUTOR` |
| **graph_delta** | `docs/_tech_graph/86_sandbox_capabilities.graph.yaml` |
| **freeze_id** | `v0.9.4` |
| **test_strategy** | `required` |
| **failure_paths** | 见下文 |

### 人工闸 `human_gate`

| human_gate_id | status | blocks_hats | 说明 |
| --- | --- | --- | --- |
| HG-TASK-DRAFT | `completed` | 30 | 任务已完成 |
| HG-AUDIT-R1 | `completed` | 30 | R1 已审计 |
| HG-EXEC-AUTH | `completed` | 30 | 已执行完成，测试绿 |

## 背景与目标

v0.8.2 已引入 `DockerExecutor` / `FirejailExecutor` 沙箱原型，v0.9.2 已统一配置中心。v0.9.4 目标是在沙箱执行与策略配置之间建立显式能力（capability）契约，使安全策略从「黑白名单字符串」升级为「可声明、可校验、可审计」的结构化模型。

## 范围

### 核心

- 新增 `harness_sdk/capability.py`：
  - `Capability` 枚举/模型：`read`、`write`、`execute`、`network`、`shell`、`env`、`sudo` 等
  - `CapabilitySet`：能力集合的声明、包含、合并
  - `CommandRisk`：命令风险等级（`safe`、`restricted`、`dangerous`、`blocked`）
- 重构 `harness_sdk/safety.py`：
  - `SafetyConfig` 使用 Pydantic 模型（`BaseModel`）
  - 策略配置支持 `capabilities` 字段，替代/增强纯 `whitelist`/`blacklist`
  - 支持按 capability 评估命令风险
- 扩展沙箱执行器：
  - `DockerExecutor` 在 capability 缺失时明确拒绝（如 `network` 缺失则 `--network none`）
  - `FirejailExecutor` 根据 capability 生成 `--noblacklist` / `--whitelist` 参数
  - 校验 capability 与沙箱参数的兼容性（如 `sudo` 能力禁止在沙箱内使用）
- 审计联动：
  - 沙箱执行前写入 `CapabilityAuditEvent`
  - 记录实际授予的 capability、拒绝原因、沙箱参数
- CLI 增强：
  - 新增 `harness-probe safety show`：显示当前安全策略与能力模型
  - 新增 `harness-probe safety evaluate <cmd>`：评估命令风险等级
  - `run` / `compile` 增加 `--capability` 参数用于显式声明额外能力

### 配置与文档

- 新增 `config/capabilities.yaml`：默认能力模型定义
- 更新 `config/safety.yaml`：支持 `capabilities` 字段
- 新增 `docs/_tech_graph/86_sandbox_capabilities.graph.yaml`
- 更新 `CHANGELOG.md` 与 `pyproject.toml` 版本到 `0.9.4`

### 非范围

- 不接入真实 LLM（v0.9.9）
- 不新增除 Docker / Firejail 之外的沙箱后端
- 不修改执行器插件加载机制（v0.8.1 已稳定）
- 不修改审计事件核心模型（v0.9.3 已稳定）

## 依赖与引用

- `docs/PLAN_v0_9_to_v1_zh.md` §三、v0.9.x 详细规划
- `docs/harness/tasks/done/task_harness_probe_v0_9_3_audit_regression_fix.md`
- `harness_sdk/safety.py`
- `harness_sdk/executor_plugins/docker.py`
- `harness_sdk/executor_plugins/firejail.py`
- `harness_sdk/executor_plugins/subprocess.py`
- `harness_sdk/audit/events.py`
- `harness_probe/cli.py`
- `config/safety.yaml`

## 验收标准

- [ ] `Capability` / `CapabilitySet` / `CommandRisk` 模型完整，单测覆盖
- [ ] `SafetyConfig` 迁移为 Pydantic 模型，保留 `reload()` 热重载能力
- [ ] `config/safety.yaml` 支持 `capabilities` 字段，并向后兼容旧 `whitelist`/`blacklist`
- [ ] `DockerExecutor` 能根据 capability 设置 `--network` 与挂载策略
- [ ] `FirejailExecutor` 能根据 capability 生成 `--whitelist` / `--blacklist` 参数
- [ ] `harness-probe safety evaluate <cmd>` 返回正确风险等级
- [ ] `harness-probe safety show` 输出当前策略与能力模型
- [ ] 沙箱执行写入 `CapabilityAuditEvent` 到审计日志
- [ ] `pytest tests/ -q` 全绿
- [ ] `ruff check .` 全绿
- [ ] `mypy harness_sdk` 全绿
- [ ] 图谱与 CHANGELOG 同步更新
- [ ] 创建并推送 `task/v0-9-4-sandbox-capabilities` 分支，合并到 `main`

## 实现备忘

- 待执行后回填

## 测试策略

`required`。安全能力是 Harness 核心，必须有可失败测试覆盖：能力模型、策略评估、沙箱参数生成、CLI 输出、审计事件写入。

## 失败路径

| 触发条件 | 系统行为 | 是否可重试 | 用户可见类型 |
| --- | --- | --- | --- |
| 命令需要未声明 capability | `SafetyError` 或 `CommandRisk.blocked` | 修正配置后重试 | 错误提示 |
| 沙箱 capability 与参数冲突 | 执行前拒绝，返回错误码 | 修正 capability 后重试 | 错误提示 |
| Docker 未安装且请求 network 能力 | 降级为 `network=none` 并警告 | 安装 Docker 后重试 | 警告 |
| Firejail 在 macOS 上运行 | 明确不支持，建议使用 Docker | 切换执行器 | 错误提示 |
| safety.yaml 缺少 capabilities 字段 | 向后兼容，使用默认能力集 | 自动 | 无/信息 |

## 给 Cursor

- 只修改安全、沙箱、CLI 相关文件，不动审计核心与配置中心核心
- `SafetyConfig` 的 Pydantic 化需保持现有 public API 兼容（`load_safety_config`、`check` 等）
- 沙箱执行器保持 `async run(...) -> ExecutionResult` 接口不变
- 新增测试必须真实通过，禁止伪造结果
- 不要直接提交到 main，创建分支并推送

