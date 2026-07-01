# v0.9.0 规划 · CI 集成与 GitHub Actions

> 日期：2026-06-30  
> 类型：功能版规划（v0.9.0）  
> 目标：让 Harness Probe 可以在 GitHub Actions 中复用，提供 verify/run 的 action 与 workflow 模板

---

## 版本定位

v0.9.0 是 Harness Probe 从本地工具走向 CI/CD 集成的关键版本。基于 v0.8.x 的插件化执行器，CI 可以在不同执行器之间安全切换。

---

## 候选任务

### 9.1 · GitHub Action（P0）

- 创建 `.github/actions/harness-probe-verify/action.yml`：
  - 输入：`task`、`graph`、`wiki`、`depth`、`safety-config`
  - 输出：`verify-result`（JSON）
- 创建 `.github/actions/harness-probe-run/action.yml`：
  - 输入：`task`、`from-hat`、`to-hat`、`executor`、`preview`、`safety-config`
  - 输出：`run-result`（JSON）

### 9.2 · 示例 Workflow（P0）

- `harness-verify.yml`：PR 时校验 task 人闸与合同
- `harness-run.yml`：合并到 main 前执行验收合约
- 提供 `.github/workflows/README.md` 说明如何引用

### 9.3 · 远程仓库验证（P1）

- CLI 支持 `--repo URL` 或 `--repo-path`，在指定仓库运行 verify/run
- 临时 clone 仓库，运行后清理
- 支持 `harness-probe verify --repo cyning12/cyning-harness-probe --task task.md`

### 9.4 · CI 输出格式（P1）

- JSON 输出支持 GitHub Actions 的 `::set-output` / `$GITHUB_OUTPUT`
- 失败时生成 annotation（`::error file=...`）
- 支持 SARIF 或 Markdown 摘要

---

## 验收标准

- [ ] Action 在示例仓库可运行
- [ ] Workflow 在 PR 时能正确拦截未批准人闸的 task
- [ ] `pytest tests/ -q` 全绿
- [ ] ruff / mypy 全绿
- [ ] 文档与图谱更新

---

## 与 v1.0.0 关系

CI 集成是生产就绪的核心指标之一。v0.9.0 完成后，Harness Probe 可以宣称支持"可嵌入任意仓库的自动化验收"。
