# v0.7.x 规划草案 · 补丁与完善

> 日期：2026-06-30  
> 类型：补丁版规划（文档草案）  
> 目标：在不引入新架构的前提下，打磨 v0.7 细节

---

## 一、版本定位

v0.7.x 是 v0.7.0 的补丁线，聚焦：

- 修复 `@cyning/harness` 与 probe 的边界问题
- 完善安全执行器的可配置性
- 补文档、补测试、补示例
- 为 v0.8.0 的功能扩展扫清障碍

---

## 二、候选任务

### 7.1 · 安全策略文件（轻量）

- 支持从 `config/safety.yaml` 加载项目级白名单/黑名单
- 默认与 `SafetyConfig` 合并，项目配置可扩展但不可覆盖危险前缀
- 新增 `--safety-config` CLI 参数

### 7.2 · 执行日志增强

- 日志中增加 `hat`、`contract_ref`、`task_path`
- 支持按日期轮转：`execution_log_YYYYMMDD.jsonl`
- 提供 `harness_probe.cli logs` 子命令查看/过滤日志

### 7.3 · 错误信息可读性

- `blocked` 时返回更明确的用户提示："命令 X 因 Y 被拦截，如需放行请更新 config/safety.yaml 或使用 --safety-mode audit"
- 区分 `not_in_whitelist` 与 `dangerous_*`

### 7.4 · 文档与示例

- `examples/safety/`：展示 whitelist / audit / unsafe 三种模式
- `examples/mcp/`：展示 MCP probe_run 参数
- 更新 `README.md` FAQ

### 7.5 · 测试补强

- 增加 `test_cli_safety.py`：端到端测试 CLI 安全参数
- 增加 `test_mcp_safety.py`：测试 MCP probe_run 的 dry_run / safety_mode
- 覆盖命令长度超限、危险字符组合

---

## 三、验收标准

- [ ] 所有新增能力均有自动化测试
- [ ] `pytest tests/ -q` 全绿
- [ ] `ruff` / `mypy` 全绿
- [ ] 文档与示例同步更新
- [ ] 不破坏 v0.7.0 的 CLI/MCP 接口

---

## 四、版本号建议

| 任务组合 | 版本号 |
|----------|--------|
| 仅 7.3 + 7.4 | v0.7.1 |
| 7.1 + 7.2 + 7.3 + 7.4 | v0.7.2 |
| 7.1 + 7.2 + 7.3 + 7.4 + 7.5 | v0.7.3 |

---

## 五、与 v0.8.0 的关系

v0.7.x 是 v0.8.0 的前置打磨：

- v0.7.x 完善配置与日志 → v0.8.0 引入策略热重载
- v0.7.x 补全测试 → v0.8.0 引入沙箱预览时风险可控
- v0.7.x 文档示例 → v0.8.0 对外发布/教学素材
