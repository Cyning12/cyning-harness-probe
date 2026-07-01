# task_harness_probe_v0_10_0_p0_1_ops_desk_v1

## Harness 元信息

| 字段 | 值 |
| --- | --- |
| **track** | `feature` |
| **lightweight_task** | `no` |
| **module_id** | `OPS-DESK` |
| **graph_delta** | `docs/_tech_graph/88_ops_desk.graph.yaml` |
| **freeze_id** | `v0.10.0` |
| **parent_id** | `v0.10.0-p0-2` |
| **test_strategy** | `required` |
| **failure_paths** | 见下文 |

### 人工闸 `human_gate`

| human_gate_id | status | blocks_hats | 说明 |
| --- | --- | --- | --- |
| HG-TASK-DRAFT | `pending` | 30 | 任务单已签完 draft，进入 R1 审计 |
| HG-AUDIT-R1 | `pending` | 30 | R1 审计：确认模块边界、失败路径、验收标准 |
| HG-EXEC-AUTH | `pending` | 30 | 授权 30 改码 |

---

## 背景与目标

P0-3 任务单 Schema 化与 P0-2 本地可执行验收已完成。P0-1 目标是把所有 active 任务单、人闸状态、验证结果汇总成一张**本地可运行**的 Ops Desk 看板：

- 让执行者在 30 改码前一眼看清当前阻塞点。
- 让审计者在 R1 阶段批量检查 graph_delta 与 test_strategy 合规性。
- 不引入 Web 后端/数据库，以文件和静态 HTML 为主，保证 CI/本地行为一致。

本任务把颗粒度切细到子命令级，方便逐步合并、逐条验收。

---

## 范围

### 1. 数据读取层（OpsDeskReader）

新增 `harness_probe/ops_desk/reader.py`（或 `harness_probe/ops_desk.py` 中的 `OpsDeskReader`）：

- 扫描 `docs/harness/tasks/active/` 与 `docs/harness/tasks/done/`（可配置）。
- 对每个 `task_*.md` 调用 `harness_sdk.task_parser.parse_task_file`。
- 收集：任务路径、模块、标题、freeze_id、graph_delta、test_strategy、人闸状态、验收标准、失败路径。
- 错误处理：解析失败的文件单独进入 `errors` 列表，附带文件路径和错误信息。

### 2. 核心模型（OpsDesk Models）

新增 `harness_probe/ops_desk/models.py`：

- `TaskRow`：单个任务的可视化行（path / title / module / freeze_id / graph_delta / test_strategy / gate_status / blockers）。
- `OpsDeskSnapshot`：所有任务 + 汇总（active 数、done 数、阻塞 30 的任务数、graph_delta 缺失数）。
- `OpsDeskExport`：导出 HTML/Markdown/JSON 的统一模型。

### 3. CLI 子命令：`ops-desk show`

扩展 `harness_probe/cli.py`：

- `harness-probe ops-desk show`：列出所有 active 任务、人闸状态、阻塞点。
- 输出格式：`--format markdown`（默认）或 `--format json`。
- 列：任务相对路径、模块、标题、freeze_id、test_strategy、人闸状态（HG-AUDIT-R1 等）、是否阻塞 30。

### 4. CLI 子命令：`ops-desk blockers`

- `harness-probe ops-desk blockers`：只输出会阻塞 hat 30 的任务和人闸。
- 支持 `--format json|markdown`。
- 失败路径：若无人闸阻塞，给出友好提示（F6）。

### 5. CLI 子命令：`ops-desk graph`

- `harness-probe ops-desk graph`：校验所有 active 任务引用的 `graph_delta` 文件是否存在。
- 输出：缺失文件列表、每个任务的 `graph_delta` 状态。
- 支持 `--format json|markdown`。

### 6. 静态 HTML 导出（可选但推荐）

- `harness-probe ops-desk export --html ops/index.html`：生成单页静态 HTML 看板。
- HTML 包含：任务表格、阻塞高亮、graph_delta 状态、验收标准进度。
- 不依赖服务端，CI 可直接打开查看。

### 7. 配置与图谱

- 新增 `docs/_tech_graph/88_ops_desk.graph.yaml`。
- 更新 `CHANGELOG.md` v0.10.0 章节，记录 P0-1 完成。
- 可选：更新 `README.md` v0.10.0 使用示例。

### 非范围

- 不接入真实 LLM（v0.9.9 / v1.0.0）。
- 不实现持久化数据库或 Web 后端。
- 不修改 `harness_probe/verify.py` 的核心逻辑（只复用结果）。
- 不修改任务单 Schema 模型（P0-3 已稳定）。
- 不发布 npm 包。

---

## 依赖与引用

- `docs/PLAN_v0_10_0_zh.md` §P0-1
- `docs/harness/HARNESS_V2_PLAN.md` §5
- `harness_sdk/task_schema.py`（P0-3）
- `harness_sdk/task_parser.py`（P0-3）
- `harness_probe/verify.py`（P0-2）
- `harness_probe/cli.py`
- `docs/_tech_graph/89_verify.graph.yaml`
- `docs/_tech_graph/92_task_schema.graph.yaml`

---

## 验收标准

- [ ] `harness_probe/ops_desk/reader.py` 能扫描 active/done 并解析任务单。
- [ ] `harness-probe ops-desk show` 对合法任务目录返回 0。
- [ ] `harness-probe ops-desk show` 输出包含 HG-AUDIT-R1 状态与阻塞 30 标志。
- [ ] `harness-probe ops-desk blockers` 只输出阻塞 30 的任务。
- [ ] `harness-probe ops-desk graph` 能检测缺失的 `graph_delta`。
- [ ] `harness-probe ops-desk graph --format json` 输出可解析的 JSON。
- [ ] `harness-probe ops-desk export --html <path>` 生成可打开的单页 HTML。
- [ ] `pytest tests/ -q` 全绿。
- [ ] `ruff check .` 全绿。
- [ ] `mypy harness_sdk` 全绿。
- [ ] 新增 `docs/_tech_graph/88_ops_desk.graph.yaml`。
- [ ] `CHANGELOG.md` v0.10.0 章节包含 P0-1 完成记录。
- [ ] 新增 `tests/test_ops_desk.py` 覆盖 show / blockers / graph / export。

---

## 失败路径

| ID | 触发条件 | 系统行为 | 可重试 | 用户可见 |
| --- | --- | --- | --- | --- |
| F1 | 任务单 YAML 解析失败 | 跳过该文件，记录到 errors 列表 | 修正后重试 | 文件路径 + 错误信息 |
| F2 | 人闸阻塞 30 | 在 show/blockers 中高亮 | 人工审批后重试 | 明确 blocker 列表 |
| F3 | `graph_delta` 文件缺失 | graph 子命令标记失败 | 补图后重试 | 缺失文件路径 |
| F4 | active 目录为空 | show 输出空列表并提示 | 自动 | 友好提示 |
| F5 | 导出 HTML 目录不可写 | export 报错并退出 | 修正目录权限后重试 | 路径 + 错误信息 |
| F6 | 无阻塞 30 的人闸 | blockers 输出 "No blockers found" | 自动 | 友好提示 |

---

## 推荐拆分顺序

建议按以下子任务（sub-tasks）执行，每个子任务可独立合并：

1. **p0-1-1**：数据读取层 — `harness_probe/ops_desk/reader.py` + 基本模型。
2. **p0-1-2**：`ops-desk show` CLI + Markdown/JSON 输出。
3. **p0-1-3**：`ops-desk blockers` CLI。
4. **p0-1-4**：`ops-desk graph` CLI。
5. **p0-1-5**：静态 HTML 导出 `ops-desk export --html`。
6. **p0-1-6**：测试 `tests/test_ops_desk.py` + 图谱/CHANGELOG 更新 + 提交分支。

---

## 自检结论（执行者）

- 待回填

---

## 修订记录

| 日期 | 版本 | 修订人 | 说明 |
| --- | --- | --- | --- |
| 2026-07-01 | v1.0.0 | Hermes | 初始任务单，基于 PLAN_v0_10_0_zh.md P0-1 制定，细分为 6 个子任务 |

