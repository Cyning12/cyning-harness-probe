# task_harness_probe_v0_10_0_p0_2_verify_v1

## Harness 元信息

| 字段 | 值 |
| --- | --- |
| **track** | `feature` |
| **lightweight_task** | `no` |
| **module_id** | `VERIFY` |
| **graph_delta** | `docs/_tech_graph/89_verify.graph.yaml` |
| **freeze_id** | `v0.10.0` |
| **parent_id** | `v0.10.0-p0-3` |
| **test_strategy** | `required` |
| **failure_paths** | 见下文 |

### 人工闸 `human_gate`

| human_gate_id | status | blocks_hats | 说明 |
| --- | --- | --- | --- |
| HG-TASK-DRAFT | `approved` | 30 | 任务单已定稿 |
| HG-AUDIT-R1 | `approved` | 30 | R1 审计通过：verify 子命令范围、失败路径、验收标准清晰 |
| HG-EXEC-AUTH | `approved` | 30 | 已授权 30 改码 |

---

## 背景与目标

P0-3 已完成任务单 Schema 与 `harness-probe task validate`。P0-2 目标是在此基础上实现本地可执行验收：

- 对给定任务单运行一套标准化验证流程。
- 与 CI 共享同一套核心逻辑，保证本地/远程行为一致。
- 输出结构化 `VerifyReport`，供 Ops Desk（P0-1）消费。

v0.9.5 配置中心增强已提供 `ConfigManager`，本任务在 verify 中仅一次性读取，不启用 watch。

---

## 范围

### 核心

1. **新增 `harness_probe/verify.py` 模块**
   - `VerifyReport` Pydantic 模型：
     - `task_path: str`
     - `passed: bool`
     - `blockers: list[str]`
     - `checks: list[VerifyCheck]`（name / passed / message / duration_ms）
     - `summary: str`
   - `VerifyCheck`：单个检查项结果。
   - `verify_task(task_path, graph_root, strict=False, env=None) -> VerifyReport`：
     - 解析任务单 YAML frontmatter 与正文
     - 检查人闸是否阻塞 hat 30
     - 检查 `graph_delta` 文件是否存在
     - 检查 `test_strategy` 合法
     - 若 `test_strategy == 'required'`，检测是否有对应测试文件（命名启发式：任务单文件名去 `task_` 前缀并映射到 `tests/test_*.py`）
     - 运行 `pytest tests/ -q`
     - 运行 `ruff check .`
     - 运行 `mypy harness_sdk`
   - `verify_graph_delta(task_path, graph_root) -> VerifyCheck`：校验图谱文件存在。
   - `verify_human_gates(task_path) -> VerifyCheck`：返回阻塞 30 的闸列表。

2. **CLI 新增 `harness-probe verify` 子命令**
   - `harness-probe verify --task <path>`
   - `harness-probe verify --dir <path>`（批量验证，返回汇总）
   - `--format json|markdown`（默认 markdown）
   - `--ci`：失败时非 0 退出码，输出精简
   - `--strict`：将人闸 `completed` 视为非法（复用 P0-3 能力）
   - `--env <env>`：使用 `ConfigManager` 多环境能力
   - 输出到 stdout；`--ci` 模式下仅输出失败项和 summary。

3. **测试**
   - 新增 `tests/test_verify.py`：
     - 合法任务单验证通过
     - `graph_delta` 缺失时失败
     - 人闸阻塞 30 时失败
     - `--ci` 模式返回非 0 退出码
     - JSON/markdown 输出格式正确
     - 批量 `--dir` 模式正确汇总

4. **文档/图谱**
   - 新增 `docs/_tech_graph/89_verify.graph.yaml`
   - 更新 `CHANGELOG.md` v0.10.0 章节
   - 更新 `README.md` 中 v0.10.0 使用示例

### 非范围

- 不接入真实 LLM（v0.9.9 / v1.0.0）
- 不实现 Ops Desk 看板（P0-1）
- 不修改任务单 Schema 模型（P0-3 已稳定）
- 不引入数据库或 Web 后端
- 不发布 npm 包

---

## 依赖与引用

- `docs/PLAN_v0_10_0_zh.md` §P0-2
- `docs/harness/HARNESS_V2_PLAN.md` §5
- `harness_sdk/task_schema.py`（P0-3）
- `harness_sdk/task_parser.py`（P0-3）
- `harness_sdk/config.py`（v0.9.5）
- `harness_probe/cli.py`
- `docs/_tech_graph/92_task_schema.graph.yaml`

---

## 验收标准

- [ ] `harness_probe/verify.py` 实现 `VerifyReport` 与 `verify_task`
- [ ] `harness-probe verify --task <task>` 对合法任务单返回 0
- [ ] `harness-probe verify --ci` 失败时返回非 0 退出码
- [ ] `harness-probe verify --dir docs/harness/tasks/active` 批量验证并输出汇总
- [ ] `--format json` 输出可被解析的 JSON
- [ ] `--format markdown` 输出人类可读的表格
- [ ] `graph_delta` 缺失时报告明确 blocker
- [ ] 人闸阻塞 30 时拒绝运行并列出 blocker
- [ ] `test_strategy=required` 但无对应测试时报告失败
- [ ] `pytest tests/ -q` 全绿
- [ ] `ruff check .` 全绿
- [ ] `mypy harness_sdk` 全绿
- [ ] 新增 `docs/_tech_graph/89_verify.graph.yaml`
- [ ] `CHANGELOG.md` v0.10.0 章节包含 P0-2 完成记录
- [ ] 创建并推送 `task/v0-10-0-p0-2-verify` 分支

---

## 失败路径

| ID | 触发条件 | 系统行为 | 可重试 | 用户可见 |
| --- | --- | --- | --- | --- |
| F1 | 任务单 YAML 解析失败 | `verify` 报错并指出文件/行号 | 修正后重试 | 字段级错误 |
| F2 | 人闸阻塞 30 执行 | `verify` 输出 blocker 列表并退出 | 人工审批后重试 | blocker 列表 |
| F3 | `graph_delta` 文件缺失 | 标记为 failed，写入 checks | 补图后重试 | 缺失文件路径 |
| F4 | `test_strategy=required` 但无测试 | 标记为 failed | 补充测试后重试 | 缺少测试文件清单 |
| F5 | pytest/ruff/mypy 失败 | 报告具体失败项 | 修复代码后重试 | 详细错误输出 |
| F6 | `--dir` 目录为空 | 输出空报告并提示 | 自动 | 友好提示 |

---

## 实现备忘

- 待执行

---

## 测试策略

`required`。

- 单元测试覆盖 `VerifyReport` 模型序列化、`verify_task` 各分支。
- CLI 端到端测试覆盖 `--task`、`--dir`、`--format`、`--ci`。
- 全量验证：
  - `pytest tests/ -q`
  - `ruff check .`
  - `mypy harness_sdk`

---

## 自检结论（执行者）

- 待回填

---

## 修订记录

| 日期 | 版本 | 修订人 | 说明 |
| --- | --- | --- | --- |
| 2026-07-01 | v1.0.0 | Hermes | 初始任务单，基于 PLAN_v0_10_0_zh.md P0-2 制定 |
