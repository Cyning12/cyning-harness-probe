# v0.9 到 v1.0.0 长期规划 · 执行器插件化、CI 集成与生产就绪

> 日期：2026-06-30  
> 类型：长期路线图（v0.8.x / v0.9.x / 1.0.0）  
> 目标：在 v0.8.0 沙箱预览与热重载基础上，逐步完成插件化、CI 集成、稳定性与文档，迈向 1.0.0 生产就绪

---

## 一、版本定位总览

| 版本 | 主题 | 定位 |
|------|------|------|
| v0.8.1 | 执行器插件化初版 | 把 `SubprocessExecutor` 重构为插件体系，支持 `DryRunExecutor`、`PreviewExecutor`、`SubprocessExecutor` |
| v0.8.2 | 沙箱执行器原型 | 引入 `DockerExecutor` / `FirejailExecutor` 沙箱接口，默认不启用 |
| v0.9.0 | CI 集成与 GitHub Actions | 提供可复用 action、workflow 模板与远程仓库验证 |
| v0.9.1 | 日志审计与报告 | 执行日志查询、审计摘要、安全报告导出 |
| v0.9.2 | 配置与策略增强 | 多环境配置、策略继承、YAML schema 校验 |
| v1.0.0 | 生产就绪 | 稳定 API、完整文档、性能基线、回滚策略、正式发布 |

---

## 二、v0.8.x 详细规划

### v0.8.1 · 执行器插件化（P0）

- 定义 `VerifyExecutor` 协议：
  - `async run(cmd, cwd, session_id) -> ExecutionResult`
  - `supports(cmd) -> bool`
  - `describe() -> str`
- 内置插件：
  - `DryRunExecutor`（mock，返回 dry-run 结果）
  - `PreviewExecutor`（只分析不执行）
  - `SubprocessExecutor`（当前真实执行）
- CLI `--executor-plugin` 参数选择插件
- `config/executor.yaml` 配置默认插件
- 插件加载优先顺序：CLI 参数 > 配置文件 > 环境变量 > 默认 `SubprocessExecutor`

### v0.8.2 · 沙箱执行器原型（P1）

- 新增 `SandboxExecutor` 抽象基类
- 提供 `DockerExecutor` 实现：
  - 在临时容器内执行命令
  - 限制网络、CPU、内存
  - 超时与资源回收
- 提供 `FirejailExecutor` 实现：
  - 利用 firejail 做 Linux 沙箱（可选）
  - macOS 降级为 Docker 或提示不支持
- 默认不启用，需要 `--executor-plugin docker` 或环境变量显式开启

---

## 三、v0.9.x 详细规划

### v0.9.0 · CI 集成与 GitHub Actions（P0）

- 提供 `.github/actions/harness-probe-verify/action.yml`：
  - 输入：`task`、`graph`、`wiki`、`depth`
  - 输出：verify 结果、是否通过
- 提供示例 workflow：
  - `harness-verify.yml`：PR 前校验 task 人闸
  - `harness-run.yml`：合并前执行验收合约
- 支持 `python -m harness_probe.cli run --dry-run` 在 CI 中运行
- 发布 npm-style 包？暂不，先提供 Python 包安装

### v0.9.1 · 日志审计与报告（P1）

- CLI `logs` 子命令：
  - `harness-probe logs --session <id>`
  - `harness-probe logs --hat 30 --status blocked`
  - `harness-probe logs --audit --session <id>`
- 安全报告导出：
  - `run --safety-report safety_report_<session>.md`
  - 包含：执行命令、拦截命令、风险统计、建议

### v0.9.2 · 配置与策略增强（P1）

- 多环境配置：`config/safety.<env>.yaml`
- 策略继承：基础配置 > 环境配置 > 项目配置
- YAML schema 校验：`SafetyConfig` 的 pydantic 模型化
- 配置热重载增强：支持 watch 多个文件

---

## 四、v1.0.0 生产就绪

### 目标

v1.0.0 意味着：
- API 稳定（不再引入破坏性变更）
- 核心功能完整：编译、执行、安全、预览、沙箱、CI、日志、报告
- 文档完整：README、API 文档、架构图谱、示例、FAQ
- 性能基线：大型 graph 下编译与执行时间可预测
- 可观测性：日志、审计、错误码体系
- 回滚策略：支持按 freeze_id 回滚配置与执行策略

### 验收标准

- [ ] 所有 v0.9.x 任务完成
- [ ] 公开 API 文档完整（harness_sdk 全部公共接口）
- [ ] 通过 100+ 自动化测试
- [ ] ruff / mypy 全绿
- [ ] 提供至少 3 个完整示例项目
- [ ] README 包含安装、快速开始、架构、贡献指南
- [ ] GitHub Releases 发布 v1.0.0
- [ ] 发布后 7 天内无 P0/P1 bug

---

## 五、推荐执行顺序

1. **v0.8.1** 执行器插件化（必须先做，v0.9.0 CI 依赖统一接口）
2. **v0.9.0** CI 集成（插件化后可直接在 CI 中切换 executor）
3. **v0.8.2** 沙箱原型（依赖插件体系）
4. **v0.9.1** 日志审计（依赖执行器统一日志格式）
5. **v0.9.2** 配置增强（策略继承需要插件化配置加载）
6. **v1.0.0** 生产就绪收尾

---

## 六、风险与依赖

| 风险 | 缓解 |
|------|------|
| Docker 沙箱在 macOS 上体验不一致 | 默认禁用，提供降级方案 |
| 插件化引入抽象层可能降低性能 | 提供基准测试，必要时允许内联默认执行器 |
| CI Action 维护成本 | 先提供示例 workflow，稳定后再发布独立 action |
| 1.0.0 范围膨胀 | 每个版本必须有明确的冻结标准，不随意加需求 |

---

## 七、版本号建议

- v0.8.1 / v0.8.2：小版本（功能增强）
- v0.9.0：中版本（CI 集成，新的使用场景）
- v0.9.1 / v0.9.2：小版本（功能增强）
- v1.0.0：大版本（API 稳定、生产就绪）
