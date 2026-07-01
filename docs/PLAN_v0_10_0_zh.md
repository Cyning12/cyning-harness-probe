# v0.10.0 规划 · Ops Desk 看板与 Harness 可执行验收

> 日期：2026-07-01  
> 类型：版本路线图（v0.10.0）  
> 目标：在 v0.9.5 配置中心增强基础上，搭建 Ops Desk 看板，将 Harness 的 Verify 支柱从 CI 流水线延伸到本地可执行验收，并为后续 LLM Provider 集成验证做准备。

---

## 一、版本定位

v0.10.0 是 **v0.9.x → v1.0.0 之间的关键中版本**，核心使命：

1. **落地 Ops Desk 看板**：把任务、人闸、图谱、验证结果整合到可本地运行的 Web/CLI 看板。
2. **可执行验收闭环**：`harness-probe verify` 子命令能真实跑验证、返回结构化结果、与 GitHub Actions 共享同一份逻辑。
3. **为 v0.9.9 / v1.0.0 的 LLM 集成验证打基础**：Ops Desk 需要能展示多任务并行状态，LLM Executor 才能被当作一个可插拔验证器接入。

---

## 二、P0 任务清单

### P0-1 · Ops Desk 看板（Ops Desk · 本地/CI 两用）

- 新增 `harness_probe/ops_desk.py` 模块：
  - 读取 `docs/harness/tasks/active/` 与 `done/` 任务单
  - 解析人闸（`human_gate`）、冻结 ID（`freeze_id`）、图谱增量（`graph_delta`）、测试策略（`test_strategy`）
  - 输出 Markdown / JSON / HTML 三种格式
- CLI 新增 `harness-probe ops-desk`：
  - `ops-desk show`：当前所有 active 任务、人闸状态、阻塞点
  - `ops-desk blockers`：列出所有 status 非 approved 且 blocks_hats 包含 30 的闸
  - `ops-desk graph`：校验 active 任务引用的 `graph_delta` 文件是否存在
- 可选：本地静态 HTML 生成（`ops-desk export --html ops/index.html`），不依赖后端服务
- 新增 `docs/_tech_graph/88_ops_desk.graph.yaml`

### P0-2 · `harness-probe verify` 可执行验收

- 新增 `harness_probe/verify.py` 模块：
  - 输入：任务单路径、图谱路径、可选 wiki 路径
  - 检查项：
    - 任务单存在且人闸字段完整
    - `graph_delta` 文件存在
    - `test_strategy` 不为空；若 `required` 必须有对应测试文件
    - 运行 `pytest tests -m <freeze_id>` 或 `pytest tests/` 全量
    - 运行 `ruff check .` 与 `mypy harness_sdk`
  - 输出：`VerifyReport` Pydantic 模型，包含 passed/failed/skipped、blockers、日志摘要
- CLI 新增 `harness-probe verify --task <path> --graph <path>`：
  - 默认本地运行，不依赖 GitHub Actions
  - 支持 `--format json|markdown`
  - 支持 `--ci` 模式：非 0 退出码 + 精简输出
- 新增测试 `tests/test_verify.py`：覆盖通过/失败路径、JSON/markdown 输出、CI 模式

### P0-3 · 任务单 Schema 与 `human_gate` 校验器

- 新增 `harness_sdk/task_schema.py`：
  - Pydantic 模型定义任务单元信息、人闸、验收标准、失败路径
  - 校验器：人闸 status 只能是 `pending`/`approved`/`completed`（兼容旧任务单），blocks_hats 必须包含 30 才允许执行
  - 与 AGENTS.md 中「闸只识别 approved/pending」的约束保持一致
- 新增 CLI `harness-probe task validate --task <path>`：
  - 检查任务单是否符合 Schema
  - 检查引用的图谱文件是否存在
- 更新 `docs/harness/prompts/TEMPLATE_task.md` 或新增模板

---

## 三、P1 任务清单

### P1-1 · 配置中心后续增强

- `.env` 文件集成：支持 `HARNESS_*` 写入 `.env` 并在 `ConfigManager` 中读取（可选，不替代环境变量）
- 敏感字段处理：`api_key`、`token` 等字段在校验时标记为 redacted，不进入 `config show`
- 多 worktree 配置隔离：在 `ConfigManager.default()` 中支持 `worktree_root` 参数

### P1-2 · GitHub Actions 可复用模板

- `.github/workflows/harness-verify.yml`：PR 时自动运行 `harness-probe verify --task <changed-task>`
- `.github/actions/harness-probe-verify/action.yml`：对外可复用 action
- 与 `harness-probe verify --ci` 共享同一套逻辑

### P1-3 · 日志审计报告（v0.9.1 规划的延续）

- `harness-probe logs --session <id>`
- `harness-probe logs --hat 30 --status blocked`
- `harness-probe safety-report --session <id>`

---

## 四、非范围

- 不接入真实 LLM（属于 v0.9.9 / pre-1.0.0）
- 不修改沙箱能力模型（v0.9.4 已稳定）
- 不引入持久化数据库或 Web 后端，Ops Desk 以文件/静态 HTML 为主
- 不发布 npm 包，保持 Python 包形态

---

## 五、依赖与引用

- `docs/harness/HARNESS_V2_PLAN.md` §5（任务单字段 `test_strategy` / `failure_paths`）
- `docs/harness/HARNESS_V2_P0_ACCEPTANCE.md`
- `docs/harness/tasks/active/` 现有任务单
- `docs/_tech_graph/` 图谱目录
- `harness_sdk/config.py`（v0.9.5 新增的热重载与多环境能力）
- `harness_probe/cli.py`

---

## 六、验收标准

- [ ] `harness-probe ops-desk show` 能列出所有 active 任务与人闸状态
- [ ] `harness-probe ops-desk blockers` 只输出阻塞 30 执行的闸
- [ ] `harness-probe ops-desk graph` 能检测缺失的 `graph_delta`
- [ ] `harness-probe verify --task <task>` 在本地跑通测试/lint/mypy 并返回报告
- [ ] `harness-probe verify --ci` 失败时返回非 0 退出码
- [ ] `harness-probe task validate` 能指出 Schema 错误和缺失图谱
- [ ] `pytest tests/ -q` 全绿
- [ ] `ruff check .` 全绿
- [ ] `mypy harness_sdk` 全绿
- [ ] 新增 `docs/_tech_graph/88_ops_desk.graph.yaml` 与 `docs/_tech_graph/89_verify.graph.yaml`
- [ ] `CHANGELOG.md` 更新 v0.10.0 章节

---

## 七、失败路径

| 触发条件 | 系统行为 | 是否可重试 | 用户可见类型 |
| --- | --- | --- | --- |
| 任务单 YAML 解析失败 | `task validate` 报错，指出文件与行号 | 修正后重试 | 字段级错误 |
| 人闸状态阻塞 30 执行 | `verify` 输出 blocker 并拒绝运行 | 人工审批后重试 | 明确 blocker 列表 |
| `graph_delta` 文件缺失 | `verify` / `ops-desk graph` 标记失败 | 补图后重试 | 缺失文件路径 |
| `test_strategy=required` 但无测试 | `verify` 失败 | 补充测试后重试 | 缺少测试文件清单 |
| pytest/ruff/mypy 失败 | `verify` 报告具体失败项 | 修复代码后重试 | 详细错误输出 |
| 无 active 任务 | `ops-desk show` 输出空列表并提示 | 自动 | 友好提示 |

---

## 八、推荐执行顺序

1. **P0-3** 任务单 Schema + `task validate`（先定义 Ops Desk 与 verify 的输入契约）
2. **P0-2** `harness-probe verify`（可执行验收是核心）
3. **P0-1** Ops Desk 看板（依赖任务单解析与 verify 结果）
4. **P1-1** 配置中心后续（`.env`、敏感字段、worktree）
5. **P1-2** GitHub Actions 模板
6. **P1-3** 日志审计报告

---

## 九、风险与依赖

| 风险 | 缓解 |
|------|------|
| 任务单格式不统一导致解析失败 | 先 Schema 化，旧任务单通过 `task validate` 逐步修正 |
| Ops Desk 范围膨胀成完整 Web 应用 | 限定为本地 CLI + 静态 HTML 导出 |
| verify 与 CI 行为不一致 | 两者共用 `harness_probe/verify.py` 核心逻辑 |
| 与 v0.9.5 配置中心热重载冲突 | 在 verify 中不启用 watch，仅使用 `ConfigManager.default()` 一次性读取 |

---

## 十、版本号说明

v0.10.0 作为中版本，标志着 Harness 从「功能增强」进入「工程验收与运营看板」阶段。它不会破坏 v0.9.5 的 public API，但会新增多个 CLI 子命令与模块，为 v0.9.9 LLM 验证和 v1.0.0 生产就绪提供基础设施。

---

## 十一、修订记录

| 日期 | 版本 | 修订人 | 说明 |
| --- | --- | --- | --- |
| 2026-07-01 | v0.1.0-draft | Hermes | 初始规划，基于 v0.9.5 合并后状态制定 |
