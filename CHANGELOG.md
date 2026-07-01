# Changelog

## v0.9.3 · 2026-07-01

### Fixed

- **审计模块回归修复**：v0.9.2 合并不慎丢失了 v0.9.1 审计子命令，本版本恢复全部能力并整合到配置中心。
  - 恢复 `harness_sdk/audit/__init__.py`、`events.py`、`reader.py`、`report.py`、`retention.py`。
  - `AuditLogger` 统一使用 `HARNESS_AUDIT_LOG_DIR` 环境变量或 `harness.audit.log_dir` 配置。
  - `AuditReader` 与 `AuditReport` 默认同样读取上述环境变量/配置，保证 CLI 与 SDK 读取同一目录。
  - `harness_probe/cli.py` 恢复 `audit` 子命令（`list`/`show`/`report`/`config`）并集成 `--no-audit` 开关。

### Changed

- 审计 CLI 命令统一使用 `AuditLogger()` 默认实例，行为与环境变量一致。

## v0.9.2 · 2026-07-01

### Added

- **配置中心（9.5）**：新增 `harness_sdk/config.py` 作为统一配置入口。
  - 统一加载 `config/*.yaml`，支持 `harness:` 包裹格式与遗留文件名推断命名空间。
  - 支持环境变量 `HARNESS_*` 覆盖，精确映射 `HARNESS_EXECUTOR_DEFAULT_PLUGIN`、`HARNESS_AUDIT_LOG_DIR`、`HARNESS_SAFETY_MODE` 等键。
  - 优先级：默认值 < 配置文件 < 环境变量 < 命令行参数。
  - 提供配置校验与友好错误提示（`ConfigError`）。
- **配置审计与示例**：新增 `config/audit.yaml` 与 `docs/examples/config/README.md`。
- **CLI 配置命令**：`harness-probe config validate` / `harness-probe config show`（支持 `json`/`yaml`/`markdown`）。
- **配置图谱**：新增 `docs/_tech_graph/95_config.graph.yaml`，并在 `00_main.graph.yaml` 中接入 `CONFIG` 节点。
- **测试覆盖**：新增 `tests/test_config_manager.py` 与 `tests/test_cli_config.py`。

### Changed

- `harness_sdk/executor_plugins/_loader.py` 完全通过 `ConfigManager` 解析默认插件，移除直接读取 `os.environ`。
- `harness_probe/cli.py` 使用 `ConfigManager` 解析 `--executor-plugin`、安全模式与默认 graph/wiki 路径。
- `harness_sdk/audit/logger.py` 与 `harness_sdk/safety.py` 通过配置中心读取配置，保留 `SafetyConfig.reload()` 热重载能力。

### Fixed

- 环境变量 `HARNESS_EXECUTOR_DEFAULT_PLUGIN` 现在正确覆盖 `harness.executor.default_plugin`（不再被拆分为 `default.plugin`）。

## v0.8.2 · 2026-07-01

### Added

- **沙箱执行器原型（8.4）**：在执行器插件化基础上新增 `SandboxExecutor` 抽象基类。
  - 通用沙箱参数：`image`、`timeout`、`network`、`memory`、`cpu`。
  - `SandboxConfigError`：参数非法或环境不满足时给出明确错误。
- **`DockerExecutor`**：`harness_sdk/executor_plugins/docker.py`，基于 `docker run` 在临时容器内执行命令。
  - 默认禁用容器网络，限制内存与 CPU。
  - 超时后回收容器并返回 `ExecutionResult.timed_out=True`。
  - Docker 未安装时提示安装。
- **`FirejailExecutor`**：`harness_sdk/executor_plugins/firejail.py`（Linux only）。
  - 使用 `firejail --noprofile --net=none` 做进程级沙箱。
  - macOS 上给出明确错误，建议改用 Docker。
- **插件加载**：`_loader.py` 注册 `docker` / `firejail` 内置插件；支持 `config/executor.yaml` 中 `sandbox` 默认配置。
- **CLI 沙箱参数**：`harness_probe/cli.py` 新增 `--sandbox-image`、`--sandbox-timeout`、`--sandbox-no-network`、`--sandbox-memory`，透传给沙箱执行器。
- **沙箱测试**：`tests/test_sandbox_executor.py` 覆盖 Docker 运行、参数解析、环境缺失错误。
  - 默认跳过 Docker 测试；启用需设置 `HARNESS_TEST_DOCKER=1`。
- **使用示例**：新增 `docs/examples/sandbox/README.md`。

### Changed

- `config/executor.yaml` 增加 `docker` / `firejail` 插件映射与 `sandbox` 默认配置段。
- `docs/_tech_graph/90_executor.graph.yaml` 更新以反映沙箱执行器节点与依赖。

## v0.8.1 · 2026-07-01

### Added

- **执行器插件化（8.3）**：`harness_sdk/executor_plugins/` 新增插件体系。
  - 定义 `VerifyExecutor` 协议：`run()` / `supports()` / `describe()`。
  - `DryRunExecutor`：不执行命令，返回 `[dry-run] <cmd>`。
  - `PreviewExecutor`：不执行命令，返回命令沙箱预览报告。
  - `SubprocessExecutor` 迁移为插件，保留原有安全校验、超时、日志功能。
  - 新增 `load_executor_plugin(name)` 工厂，支持 `config/executor.yaml` 与 `HARNESS_EXECUTOR_PLUGIN` 环境变量。
- **CLI 插件集成**：`harness_probe/cli.py` 新增 `--executor-plugin {dry-run,preview,subprocess}`。
  - 保留 `--executor {mock,real}` 向后兼容：`mock` 映射到 `dry-run`，`real` 映射到 `subprocess`。
  - 插件解析优先级：`--executor-plugin` > `--executor` 兼容映射 > `config/executor.yaml` > `HARNESS_EXECUTOR_PLUGIN` > 默认 `subprocess`。
- **默认执行器配置**：新增 `config/executor.yaml`，可配置 `default_plugin` 与自定义插件类映射。

### Changed

- `harness_sdk/executor.py` 改为兼容层，继续导出 `SubprocessExecutor` / `VerifyExecutor` 等 public API，内部委托给插件实现。
- `--preview` 模式改用 `PreviewExecutor` 插件生成沙箱报告，行为与 v0.8.0 一致。

### Fixed

- 未知插件名抛出 `ExecutorPluginError`，CLI 统一退出码 2。
- 插件配置损坏时回退到默认 `subprocess` 并发出警告。

## v0.8.0 · 2026-06-30

### Added

- **策略热重载（8.1）**：`harness_sdk/safety.py` 的 `SafetyConfig` 新增显式 `reload()` 方法，从原始 `path` 重新加载白名单/黑名单。
  - CLI 新增 `--safety-reload`：在构建 executor 前重新加载 `--safety-config` 指定的策略文件。
  - 重载失败（YAML 损坏）时保留上一次有效配置并返回 `False`。
- **沙箱预览（8.2）**：真实执行前生成命令影响报告，不执行任何命令。
  - `SubprocessExecutor.preview()` 返回命令解析、命中白名单/黑名单、建议模式与风险等级（low/medium/high）。
  - CLI 新增 `--preview` / `--preview-format`（json / markdown），与 `--executor real` 同时指定时优先 preview 并发出警告。
  - `harness_mcp/tools.py` 的 `probe_run` 新增 `preview` / `preview_format` 参数。
- **显式 AcceptanceContract verify**：`harness_sdk/compiler.py` 在 task 含显式 `## AcceptanceContract` 表时，按 `ref` 覆盖 failure_paths 自动推断的 verify 命令，使预览可反映任务作者指定的真实命令。

## v0.7.1 · 2026-06-30

### Added

- **安全策略配置**：`harness_sdk/safety.py` 新增 `load_safety_config` / `SafetyConfigError`。
  - 支持从 `config/safety.yaml` 加载自定义白名单与黑名单。
  - 项目白名单追加到默认白名单，危险前缀黑名单追加到默认黑名单。
  - 危险命令前缀（如 `rm`）被覆盖时发出 `UserWarning`。
- **CLI 安全参数**：`harness_probe/cli.py` 新增 `--safety-config`。
- **MCP 安全参数**：`harness_mcp/tools.py` 的 `probe_run` 新增 `safety_config` / `safety_mode`。
- **事件循环兼容**：`TaskRunner._run_executor` 在已有事件循环环境中通过后台线程运行 executor。
- **Wiki 加载容错**：`load_wiki_stub` 在文件缺失时返回空列表。

## v0.7 · 2026-06-30

### Added

- **安全执行器**：`harness_sdk/safety.py` 新增 `CommandSafetyChecker`。
  - 支持三种模式：`whitelist`（默认）、`audit`、`unsafe`。
  - 白名单默认允许 `pytest`、`python -m pytest`、`python -m harness_probe.cli`、`echo`、`cat`、`ls`、`pwd`、`git status/diff/log`。
  - 黑名单覆盖危险 shell 元字符（`$()`、`&&`、`|`、`>` 等）与危险命令前缀（`rm`、`sudo`、`curl`、`ssh` 等）。
  - 命令长度限制默认 1024 字符。
- **dry-run 模式**：`SubprocessExecutor` 在 `dry_run=True` 时不执行命令，返回预览结果。
- **执行日志**：`SubprocessExecutor` 支持 `execution_log_dir`，所有 `executed` / `blocked` / `timeout` / `dry_run` 事件写入 `execution_log_<session_id>.jsonl`。
- **CLI 扩展**：`run` 子命令新增 `--dry-run`、`--safety-mode {whitelist,audit,unsafe}`、`--execution-log-dir PATH`。
- **MCP 扩展**：`probe_run` 新增 `dry_run`、`safety_mode`、`execution_log_dir` 参数。
- **模型扩展**：`ExecutionResult` 新增 `blocked`、`dry_run`、`reason` 字段。

### Changed

- `SubprocessExecutor` 默认启用白名单模式，旧测试需显式指定 `safety_mode="unsafe"`。
- `TaskRunner` 透传 `session_id` 给 executor 用于日志关联。

## v0.6 · 2026-06-30

### Added

- **CLI 真实执行**：`run` 子命令新增 `--executor {mock,real}`、`--max-retries N`、`--cwd PATH`。
  - 默认 `--executor mock`，行为与 v0.5 dry-run 一致。
  - `--executor real` 时创建 `SubprocessExecutor` 真实执行 `contract.verify`。
  - `--cwd` 指定真实执行的工作目录。
- **Runner 重跑逻辑**：`TaskRunner.run_sequence` 支持 `max_retries`。
  - contract 失败时最多重跑 `max_retries` 次。
  - 重跑耗尽后 `run_node.status = blocked`，`run_graph.status = blocked`。
  - 失败 contract 的 evidence 保留最后一次结果。
- **MCP Tool 扩展**：`probe_run` 支持 `executor`、`max_retries`、`cwd`；`probe_audit` 识别 blocked 节点并输出 `recommendation="打回至 30 · 补跑 verify_cmd"` 与 `next_hat="30"`。
- **端到端测试**：新增 CLI 与 MCP 对 `--executor real`、重跑、blocked 审计的覆盖。

### Changed

- `TaskRunner` 构造函数新增 `cwd` 参数。
- `SubprocessExecutor.run` 在执行 contract.verify 时透传 `cwd`。

## v0.5 · 2026-06-30

### Added

- **MCP Server**：新增 `harness_mcp/` 模块，基于 FastMCP 暴露 4 个 Tool 与 1 个 Resource。
  - Tool：`probe_compile` / `probe_run` / `probe_audit` / `probe_verify`
  - Resource：`harness://freeze_id/current`
- **可选依赖**：`pip install -e ".[mcp]"` 安装 `mcp>=1.0.0`。
- **MCP 测试**：新增 `tests/test_mcp_tools.py`、`tests/test_mcp_resources.py`。

### Changed

- CI workflow 改用 `pip install -e ".[dev,mcp]"` 以覆盖 dev + MCP 依赖。

## v0.4 · 2026-06-30

### Added

- **SDK 重构**：新增 `harness_sdk/` 无副作用核心库（models / compiler / builder / graph / runner）。
- **CLI 迁移**：新增 `harness_probe/` CLI + IO 层，命令入口从 `python -m src.probe` 迁移至 `python -m harness_probe.cli`。
- **包化**：新增 `pyproject.toml`，提供 `harness-probe` 全局命令。
- **测试分层**：拆分 `tests/test_probe.py` 为 `test_sdk_compiler.py` / `test_sdk_builder.py` / `test_sdk_graph.py` / `test_sdk_runner.py` / `test_cli.py`。

### Changed

- `TaskRunner.run_sequence` 为纯逻辑方法，返回 `TaskRunGraph`；文件持久化由 CLI 层负责。
- `BlockedError` 迁移至 `harness_sdk/exceptions.py`。

### Removed

- 旧 `src/` 目录（Phase 1 代码已迁移至 `harness_sdk/` + `harness_probe/`）。

## v0.3 · 2026-06-29

### Added

- **全帽链补齐**：`compile --hat` 支持 10-spec / 10-task / 20-review / 50-reinspect 四顶新帽。
  - `10-spec`：生成 SPEC 草案 Prompt（R0–R5、Delta、验收标准）。
  - `10-task`：生成 task 骨架 Prompt（SPEC→failure_paths 映射）。
  - `20-review`：生成审核 Prompt（approved/blocked + HG-AUDIT-R1 签收）。
  - `50-reinspect`：生成复检 Prompt（failure_path_ref 表 + independent/global 双模式）。
- **`--run` 模式**：`python -m src.probe run --from-hat 30 --to-hat 40` 串行模拟执行并落盘 task_run JSON。
- **`--watch` 模式**：`python -m src.probe watch --once` 检测 graph 与 task 的 freeze_id 漂移。
- **CLI 新增参数**：`--spec`（关联 SPEC）、`--review-target`（审核对象）、`--mode`（independent/global）、`--run-output`（关联运行记录）。

### Changed

- `builder.py`：重构为 `build_hat_prompt()` 分发函数；原 30/40 builder 保留。
- `orchestrator.py`：改用 `build_hat_prompt` + `handoff_summary`；支持 `from_hat`/`to_hat` 过滤。
- `models.py`：`HarnessTask` 新增 `spec_path`/`spec_text`/`review_target`/`run_output_path`/`reinspect_mode`。

### Commits

- `8b23630` `feat(phase1): full hat chain support · 10-spec/10-task/20-review/50-reinspect + --run + --watch`

## v0.2 · 2026-06-29

### Added

- **PRE_SPAWN_VERIFY 校验**：新增 `python -m src.probe verify --task <path>` 子命令。
  - 校验 task 是否含 `human_gate` 表。
  - 校验 `blocks_hats` 含 `30` 时是否显式含 `HG-AUDIT-R1`。
  - 对齐工作区 IMP-09 / [`PROMPT_cursor_task_chain_serial_v1.md`](https://github.com/Cyning12/cyning-ink-workspace/blob/main/docs/harness/prompts/PROMPT_cursor_task_chain_serial_v1.md) §4.5。

### Changed

- **Prompt 生成层同步 workspace Harness V2.1 模板纪律**：
  - Subagent Prompt 明确禁止在业务 `*.graph.yaml` 写 `guardrails` / `token cap` / `max_retries`。
  - 明确 Subagent 只收 `AcceptanceContract` 表，不带 `failure_paths` 全文。
  - 30 / 40 帽必须回报 `failure_path_ref` 收工表。
- 单测新增 4 个 `human_gate` 校验用例。

### Commits

- `d641b1a` `feat(probe): sync with workspace Harness V2.1 templates · human_gate validation + PRE_SPAWN_VERIFY + prompt wording`

---

## v0.1 · 2026-06-28

### Added

- 初版 Probe CLI：`compile`、`graph-query`。
- L0 子图查询、L1 AcceptanceContract 编译、L2 Wiki 摘要注入。
- KV-Cache 友好三段式 Prompt 组装。
