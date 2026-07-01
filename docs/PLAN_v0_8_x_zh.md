# v0.8.x 规划 · 执行器插件化与沙箱原型

> 日期：2026-06-30  
> 类型：短期规划（v0.8.1 / v0.8.2）  
> 目标：在 v0.8.0 安全策略与预览基础上，完成执行器插件化并引入沙箱原型  
> **状态**：v0.8.1 已完成（merged in main），v0.8.2 待启动

---

## 版本定位

v0.8.x 是 v0.9.0 CI 集成的前置阶段。通过插件化把 `SubprocessExecutor` 抽象为通用接口，后续 CI 可以在不同执行器之间切换（dry-run / preview / subprocess / sandbox）。

v0.8.1 已落地，验证了插件化可行性。v0.8.2 是沙箱执行器原型，依赖 v0.8.1 的插件体系。

---

## v0.8.1 · 执行器插件化（P0）

### 目标

- 定义统一的 `VerifyExecutor` 协议
- 内置三种插件：DryRunExecutor、PreviewExecutor、SubprocessExecutor
- 支持通过 CLI 和配置文件选择执行器

### 关键任务

- 新增 `harness_sdk/executor_plugins/__init__.py`：
  - `VerifyExecutor` 抽象协议
  - `DryRunExecutor`
  - `PreviewExecutor`
  - `SubprocessExecutor`（从现有代码迁移）
- `harness_sdk/executor.py`：
  - 保留 `SubprocessExecutor` 作为别名/兼容层
  - 新增 `load_executor_plugin(name)` 工厂函数
- `harness_probe/cli.py`：
  - `--executor` 参数支持 `mock`/`real`/`preview`/`dry-run` 以及插件名
  - 新增 `--executor-plugin` 参数
- `config/executor.yaml`：
  - 默认执行器配置
- 新增 `tests/test_executor_plugins.py`

### 验收标准

- [ ] `VerifyExecutor` 协议定义清晰
- [ ] 三种内置插件都能通过统一接口运行
- [ ] CLI `--executor` 向后兼容
- [ ] `pytest tests/ -q` 全绿
- [ ] ruff / mypy 全绿
- [ ] 图谱更新

---

## v0.8.2 · 沙箱执行器原型（P1）

### 目标

- 在插件化基础上引入沙箱执行器
- 默认不启用，需要显式指定

### 关键任务

- 新增 `harness_sdk/executor_plugins/sandbox.py`：
  - `SandboxExecutor` 抽象基类
  - `DockerExecutor`（基于临时容器）
  - `FirejailExecutor`（Linux only，可选）
- `harness_probe/cli.py`：
  - `--executor-plugin docker` 支持
  - 沙箱参数：`--sandbox-image`、`--sandbox-timeout`
- macOS 无 firejail 时友好降级
- 新增 `tests/test_sandbox_executor.py`（标记为慢测试，可选跳过）

### 验收标准

- [ ] Docker 沙箱能执行简单命令并返回结果
- [ ] Firejail 在 Linux 上可用
- [ ] macOS 有明确降级提示
- [ ] 沙箱测试不破坏默认测试套件

---

## 与后续版本关系

| 版本 | 依赖 v0.8.x 的什么 |
|------|------------------|
| v0.9.0 CI 集成 | 统一执行器接口，可在 CI 中切换 dry-run/preview/real |
| v0.9.1 日志审计 | 插件统一输出日志格式 |
| v1.0.0 | 插件化是生产就绪的基础架构 |

---

## 风险

| 风险 | 缓解 |
|------|------|
| 插件化引入性能开销 | 默认执行器保持内联，不做过度抽象 |
| 沙箱依赖 Docker 环境 | 标记为可选依赖和可选测试 |
| 向后兼容性 | `--executor mock`/`real` 行为保持不变 |
