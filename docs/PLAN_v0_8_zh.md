# v0.8.0 规划草案 · 沙箱预览与策略热重载

> 日期：2026-06-30  
> 类型：功能版规划（文档草案）  
> 目标：在 v0.7 安全执行器基础上，引入可扩展的安全策略与沙箱预览能力

---

## 一、版本定位

v0.8.0 是 v0.7 之后的功能版，聚焦：

- **策略热重载**：安全白名单/黑名单支持运行时更新
- **沙箱预览**：在真实执行前生成"命令影响报告"
- **CI 集成**：提供 GitHub Actions 可复用的 verify/run 步骤
- **执行器插件化**：为后续 Docker / nsenter / firejail 沙箱预留接口

---

## 二、候选任务

### 8.1 · 策略热重载（P0）

- `SafetyConfig` 支持从 `config/safety.yaml` 加载
- CLI `--safety-config PATH` 与 `--safety-reload` 参数
- 文件变更时自动重新加载（可选 watchdog）
- 策略合并规则：项目配置扩展默认配置，危险前缀不可覆盖

### 8.2 · 沙箱预览（P0）

- 新增 `--preview` 模式：不执行命令，输出：
  - 命令解析结果
  - 命中的白名单/黑名单规则
  - 建议的安全模式
  - 潜在风险等级（low/medium/high）
- `probe_run` 新增 `preview=True` 参数
- 输出格式：JSON / Markdown

### 8.3 · 执行器插件化（P1）

- `VerifyExecutor` 协议扩展：`supports(cmd)`、`describe()`
- 内置执行器：
  - `SubprocessExecutor`（当前）
  - `PreviewExecutor`（仅分析不执行）
  - `DryRunExecutor`（v0.7 已有）
- 预留 `SandboxExecutor` 接口（v0.9 实现）

### 8.4 · CI 集成（P1）

- 提供 `.github/actions/harness-probe-verify/action.yml`
- 提供示例 workflow：
  - `harness-verify.yml`：PR 前校验 task 人闸
  - `harness-run.yml`：合并前执行验收合约
- 支持 `npx @cyning/harness verify` 与 `python -m harness_probe.cli run --dry-run`

### 8.5 · 执行日志分析（P1）

- `harness_probe.cli logs` 子命令
- 支持按 session、hat、event、status 过滤
- 生成审计摘要：`logs --audit --session <id>`

### 8.6 · 安全报告导出（P2）

- `run` 完成后可选生成 `safety_report_<session>.md`
- 包含：执行命令列表、拦截命令列表、风险统计、建议

---

## 三、验收标准

- [ ] 策略热重载有单元测试与文件监听测试
- [ ] 沙箱预览输出结构化 JSON/Markdown
- [ ] CI Action 在示例仓库可运行
- [ ] `pytest tests/ -q` 全绿
- [ ] `ruff` / `mypy` 全绿
- [ ] 文档、示例、图谱同步更新

---

## 四、版本号建议

v0.8.0 适合作为功能版发布，因为：

- 引入新的 CLI 参数与 MCP 参数
- 新增 `PreviewExecutor` 与插件化接口
- 新增 CI Action
- 对 v0.7.x 接口向后兼容（dry-run / safety-mode 行为不变）

---

## 五、与 v0.7.x 的关系

| v0.7.x | v0.8.0 |
|--------|--------|
| 静态 `SafetyConfig` | 热重载 `SafetyConfig` |
| `--dry-run` 简单预览 | `--preview` 结构化影响报告 |
| `SubprocessExecutor` 单一实现 | 执行器插件化接口 |
| 手动运行验证 | GitHub Actions 复用 |
| 日志仅落盘 | 日志可查询/审计 |

---

## 六、风险与依赖

| 风险 | 缓解 |
|------|------|
| 策略热重载引入文件监听依赖 | 使用 `watchdog` 可选依赖，降级为手动 `--safety-reload` |
| 沙箱预览误判风险 | 明确声明"预览不做语义分析"，仅做前缀/子串匹配 |
| CI Action 维护成本 | 先提供示例 workflow，再决定是否发布独立 action |

---

## 七、推荐启动顺序

1. v0.7.x 先完成 7.1（策略文件）+ 7.2（日志增强）
2. 然后启动 v0.8.0 的 8.1（热重载）+ 8.2（沙箱预览）
3. 最后做 8.3（插件化）+ 8.4（CI）
