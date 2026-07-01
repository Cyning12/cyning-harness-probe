# task_harness_probe_v0_9_5_config_center_enhancement_v1

## Harness 元信息

| 字段 | 值 |
| --- | --- |
| **track** | `feature` |
| **lightweight_task** | `no` |
| **module_id** | `CONFIG` |
| **graph_delta** | `docs/_tech_graph/87_config_center_enhancement.graph.yaml` |
| **freeze_id** | `v0.9.5` |
| **test_strategy** | `required` |
| **failure_paths** | 见下文 |

### 人工闸 `human_gate`

| human_gate_id | status | blocks_hats | 说明 |
| --- | --- | --- | --- |
| HG-TASK-DRAFT | `approved` | 30 | 任务单已确认 |
| HG-AUDIT-R1 | `approved` | 30 | R1 审计通过：配置模型可验证，热重载与多环境兼容现有架构 |
| HG-EXEC-AUTH | `approved` | 30 | 已授权 30 改码，可派工 Claude Code |

## 背景与目标

v0.9.2 已建立统一配置中心 `ConfigManager`，但仍有三大缺口：

1. **多环境配置切换困难**：当前仅支持单份 `config/*.yaml`，无法按环境（`dev`/`test`/`prod`）隔离策略。
2. **无动态热重载**：修改 `safety.yaml` 或 `executor.yaml` 后必须重启进程，不利于长期运行的 MCP Server / Daemon 模式。
3. **Schema 校验靠手写**：`validate()` 用大量内嵌函数检查类型，容易遗漏，无法自动校验嵌套结构与插件路径。

v0.9.5 目标是把配置中心从「能加载」升级为「可验证、可切换、可热重载」的生产级配置子系统。

## 范围

### 核心

1. **Pydantic 化配置模型**
   - 在 `harness_sdk/config_models.py` 中定义嵌套模型：
     - `ExecutorConfig`（`default_plugin`, `plugins: dict[str, str]`, `sandbox: SandboxConfig`）
     - `SandboxConfig`（`image`, `timeout`, `network`, `memory`, `cpu`）
     - `AuditConfig`（`log_dir`, `retention: RetentionConfig`）
     - `SafetyRefConfig`（`mode`, `config_path`）
     - `HarnessConfig`（聚合上述模型）
   - 模型字段类型、默认值、枚举校验（如 `mode` 只能为 `whitelist`/`audit`/`unsafe`）
   - 插件路径字符串校验：必须形如 `package.module:ClassName`
2. **多环境配置**
   - `ConfigManager.default()` 支持 `env` 参数（默认 `dev`）
   - 加载顺序：`config/<file>.yaml` → `config/<file>.<env>.yaml`（后者覆盖前者）
   - 环境变量 `HARNESS_ENV` 可切换；CLI 新增 `--env` / `-e` 参数
   - 显式文件示例：
     - `config/safety.yaml`
     - `config/safety.prod.yaml`
     - `config/executor.yaml`
     - `config/executor.test.yaml`
3. **配置热重载**
   - `ConfigManager` 新增 `watch()` 与 `stop_watch()` 方法
   - 使用 `watchdog` 或轮询监听 `config/` 目录下的 `.yaml` 文件变化
   - 变化时自动重新加载配置并调用注册回调
   - 暴露 `register_on_reload(callback)` 接口供 `SafetyConfig` 等使用
   - 提供上下文管理器 `with cfg.watch(): ...`
4. **CLI 增强**
   - `harness-probe config validate`：校验当前配置并输出错误
   - `harness-probe config show`：打印当前合并后的配置（支持 `--env`）
   - `harness-probe config watch`：启动热重载监听（前台 / 后台模式）
   - `run` / `compile` / `safety` 子命令统一支持 `--env`
5. **向后兼容**
   - 保留 `ConfigManager` 现有 public API：`get()`, `set()`, `get_path()`, `to_dict()`, `validate()`
   - 保留 `DEFAULTS` 与 `_FILE_NAMESPACE` 机制
   - 未使用 Pydantic 模型的代码仍可通过 `to_dict()` 读取

### 配置与文档

- 新增 `harness_sdk/config_models.py`
- 新增 `docs/_tech_graph/87_config_center_enhancement.graph.yaml`
- 更新 `CHANGELOG.md` 与 `pyproject.toml` 版本到 `0.9.5`
- 可选示例：`config/safety.prod.yaml`（一份即可）

### 非范围

- 不修改审计事件核心模型（v0.9.3 已稳定）
- 不修改沙箱能力模型（v0.9.4 已稳定）
- 不接入真实 LLM（v0.9.9）
- 不引入外部配置服务（如 Consul/Etcd），仅本地文件 + 环境变量

## 依赖与引用

- `docs/PLAN_v0_9_to_v1_zh.md` §三、v0.9.x 详细规划
- `docs/harness/tasks/done/task_harness_probe_v0_9_2_config_center.md`
- `docs/harness/tasks/done/task_harness_probe_v0_9_4_sandbox_capabilities_v1.md`
- `harness_sdk/config.py`
- `harness_probe/cli.py`
- `pyproject.toml` / `requirements.txt`

## 验收标准

- [ ] `HarnessConfig` / `ExecutorConfig` / `SandboxConfig` / `AuditConfig` / `SafetyRefConfig` 模型完整
- [ ] Pydantic 模型能自动校验类型、枚举、插件路径格式
- [ ] `ConfigManager.default(env="test")` 正确加载 `config/*.test.yaml` 覆盖
- [ ] `HARNESS_ENV=prod` 或 `--env prod` 能切换环境
- [ ] `watch()` 在文件修改后自动重载配置
- [ ] 重载后触发已注册的回调（如 `SafetyConfig.reload()`）
- [ ] `harness-probe config validate` 输出配置错误
- [ ] `harness-probe config show` 输出合并后配置
- [ ] `pytest tests/ -q` 全绿
- [ ] `ruff check .` 全绿
- [ ] `mypy harness_sdk` 全绿
- [ ] 图谱与 CHANGELOG 同步更新
- [ ] 创建并推送 `task/v0-9-5-config-center-enhancement` 分支，合并到 `main`


## R1 审计意见

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| pydantic 依赖 | ✓ | 已声明，可复用 |
| ConfigManager 存在 | ✓ | 需新增 `env` 参数与 `watch()` 方法 |
| 手写 `validate()` | 需替换 | 保留返回 `list[str]` 的 public API |
| 多环境文件覆盖 | 需实现 | 加载顺序：base.yaml → base.<env>.yaml → env vars → CLI args；覆盖时深合并 |
| `watchdog` 依赖 | 需新增 | 推荐加为可选依赖；未安装时轮询降级 |
| CLI `--env` | 需扩散 | 在 `run`/`compile`/`safety`/`config` 等子命令统一添加 |
| reload 回调注册 | 需实现 | `SafetyConfig.reload()` 等可通过 `register_on_reload` 接入 |
| 向后兼容 | 要求 | `ConfigManager.get/set/get_path/to_dict` 必须保留 |

### 给执行 Agent 的额外约束

1. 新增 `harness_sdk/config_models.py` 定义 Pydantic 模型；不要破坏 `ConfigManager` 现有 API。
2. `ConfigManager.validate()` 在内部调用 Pydantic 校验，但对外仍返回 `list[str]`。
3. 热重载使用 `watchdog` 优先；若未安装，使用轮询（1s）并发出 `UserWarning`。
4. 文件写入防抖：0.5s debounce，避免读取半写 YAML。
5. 多环境文件示例：创建 `config/executor.test.yaml` 用于测试，不要提交敏感 prod 配置。
6. 新增测试覆盖：模型校验、环境覆盖、热重载、CLI `config validate`/`show`。

## 实现备忘

（由 30-执行 Agent 在编码过程中回填）

## 测试策略

`required`。配置中心是 Harness 基础设施，必须有可失败测试覆盖：
- Pydantic 模型校验（正常与非法输入）
- 多环境文件加载与覆盖优先级
- 环境变量 `HARNESS_ENV` 与 CLI `--env` 优先级
- 热重载 watch 与回调触发
- `config validate` / `config show` CLI 输出

## 失败路径

| 触发条件 | 系统行为 | 是否可重试 | 用户可见类型 |
| --- | --- | --- | --- |
| YAML 格式错误 | `ConfigError` 立即抛出，CLI 非 0 退出 | 修正文件后重试 | 明确错误位置与原因 |
| 模型校验失败（如 `mode=banana`） | `config validate` 列出错误；运行时启动失败 | 修正配置后重试 | 字段级错误提示 |
| 插件路径格式错误 | Pydantic 校验拒绝 | 修正后重试 | 错误提示 |
| 环境文件不存在 | 回退到基础文件，不报错 | 自动 | 警告信息 |
| `watchdog` 未安装 | 热重载使用轮询（polling）降级，频率 1s | 自动 | 警告信息 |
| 热重载时文件写入中 | 轮询/监听防抖（debounce 0.5s）避免读取半写文件 | 自动 | 无 |

## 给 Cursor

- 只修改配置中心与 CLI 相关文件，不动审计核心、沙箱能力模型、执行器插件
- `ConfigManager` 现有 public API 必须保持兼容
- 新增 Pydantic 模型与 `ConfigManager` 的交互要可测试
- 新增测试必须真实通过，禁止伪造结果
- 不要直接提交到 main，创建分支并推送
