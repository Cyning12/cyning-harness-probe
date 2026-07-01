# task_harness_probe_v0_10_0_p0_3_task_schema_v1

## Harness 元信息

| 字段 | 值 |
| --- | --- |
| **track** | `feature` |
| **lightweight_task** | `no` |
| **module_id** | `TASK` |
| **graph_delta** | `docs/_tech_graph/92_task_schema.graph.yaml` |
| **freeze_id** | `v0.10.0` |
| **test_strategy** | `required` |
| **failure_paths** | 见下文 |

### 人工闸 `human_gate`

| human_gate_id | status | blocks_hats | 说明 |
| --- | --- | --- | --- |
| HG-TASK-DRAFT | `pending` | 30 | 待审批 |
| HG-AUDIT-R1 | `pending` | 30 | 待 R1 审计 |
| HG-EXEC-AUTH | `pending` | 30 | 待执行授权 |

---

## 背景与目标

v0.9.5 配置中心增强已经合并到 main。v0.10.0 的核心目标是建立 **Ops Desk 看板** 与 **可执行验收 `harness-probe verify`**。这两个功能都依赖对任务单的统一解析：

- 当前 `docs/harness/tasks/active/` 与 `done/` 下的任务单虽然结构相似，但字段命名、人闸状态值、`graph_delta` 路径写法并不完全一致。
- `harness-probe verify` 需要判断「人闸是否阻塞 hat 30」、「`test_strategy` 是否合法」、「`graph_delta` 是否存在」。
- 如果没有统一 Schema，每个消费任务单的模块都要写防御代码，容易遗漏、难以维护。

P0-3 目标是把任务单从「自由 Markdown」升级为「Schema 化数据」：先定义 Pydantic 模型，再提供 `harness-probe task validate` CLI，最后逐步修正现有任务单使其通过校验。

---

## 范围

### 核心

1. **任务单 Pydantic 模型**
   - 在 `harness_sdk/task_schema.py` 中定义：
     - `HumanGate`：human_gate_id / status / blocks_hats / 说明
     - `AcceptanceItem`：验收项（`- [ ]` 文本与勾选状态）
     - `FailurePath`：触发条件 / 系统行为 / 是否可重试 / 用户可见类型
     - `TaskInfo`：任务元信息、背景、范围、验收标准、失败路径、实现备忘
     - `TaskSchema`：顶层模型，包含 metadata + content 字典
   - 兼容旧字段：如 `completed` 状态自动映射为 `approved`（写入时发出 warning）
   - 校验规则：
     - `status` ∈ {`pending`, `approved`, `completed`}
     - `blocks_hats` 必须是整数列表，且包含 30 才阻塞 hat 30 执行
     - `graph_delta` 若存在，必须是仓库内相对路径且文件存在
     - `test_strategy` ∈ {`required`, `recommended`, `not_applicable`}
     - `freeze_id` 必须与 `task_*.md` 中的版本一致（警告级别，不强求）

2. **任务单解析器**
   - 新增 `harness_sdk/task_parser.py`：
     - 从 Markdown 解析 YAML frontmatter + 正文
     - 提取验收标准中的 `- [ ]` / `- [x]` 列表
     - 提取失败路径表格（如果存在）
   - 使用 `python-frontmatter` 或自实现（控制在 50 行内，减少依赖）

3. **CLI `harness-probe task validate`**
   - 输入：任务单路径或目录
   - 输出：字段级错误 / 缺失文件 / 人闸阻塞情况
   - 支持 `--format json|markdown`
   - 支持 `--strict`：将 `completed` 视为非法，强制使用 `approved`

4. **向后兼容**
   - 不删除任何现有任务单文件
   - 不强制一次性全部修正；`task validate` 先输出问题清单
   - 新增 `harness_sdk/task_schema.py` 不破坏其他模块 API

### 配置与文档

- 新增 `harness_sdk/task_schema.py`
- 新增 `harness_sdk/task_parser.py`
- 新增 `docs/_tech_graph/92_task_schema.graph.yaml`
- 更新 `CHANGELOG.md` v0.10.0 章节
- 可选：新增 `docs/harness/prompts/TEMPLATE_task_v2.md`（推荐 Schema 字段）

### 非范围

- 不修改 Ops Desk 看板（P0-1）
- 不实现 `harness-probe verify`（P0-2）
- 不接入真实 LLM
- 不引入数据库或 Web 后端
- 不强制一次性迁移所有旧任务单（本任务只提供工具和 Schema）

---

## 依赖与引用

- `docs/PLAN_v0_10_0_zh.md` §P0-3
- `docs/harness/HARNESS_V2_PLAN.md` §5（任务单字段定义）
- `docs/harness/HARNESS_V2_P0_ACCEPTANCE.md`
- `docs/harness/tasks/active/` 与 `docs/harness/tasks/done/`
- `docs/_tech_graph/` 图谱目录
- `harness_probe/cli.py`

---

## 验收标准

- [ ] `TaskSchema` / `TaskInfo` / `HumanGate` / `AcceptanceItem` / `FailurePath` 模型完整
- [ ] 模型能自动校验 `status`、`blocks_hats`、`test_strategy`、`graph_delta` 路径
- [ ] `task_parser.py` 能正确解析现有任务单的 YAML frontmatter 和 `- [ ]` 验收项
- [ ] `harness-probe task validate --task <path>` 对合法任务单返回 0，对非法任务单返回非 0
- [ ] `harness-probe task validate --dir docs/harness/tasks/active` 能批量扫描并输出问题清单
- [ ] `--strict` 模式下 `completed` 人闸状态被标记为非法
- [ ] `pytest tests/ -q` 全绿
- [ ] `ruff check .` 全绿
- [ ] `mypy harness_sdk` 全绿
- [ ] 新增 `docs/_tech_graph/92_task_schema.graph.yaml`
- [ ] `CHANGELOG.md` v0.10.0 章节包含 P0-3 完成记录

---

## R1 审计意见

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| 任务单字段是否有标准定义 | ✓ | HARNESS_V2_PLAN.md §5 已定义 |
| 现有任务单是否一致 | 需整理 | 部分旧任务单使用 `completed` / 路径写法不统一 |
| 是否需要新增依赖 | 谨慎 | 尽量用 PyYAML 自实现，避免新增 `python-frontmatter` 依赖 |
| 是否影响 verify / ops-desk | 需兼容 | Schema 是 verify 与 ops-desk 的输入契约 |
| 向后兼容 | 要求 | 不删除旧任务单，不破坏其他模块 |

### 给执行 Agent 的额外约束

1. 新增 `harness_sdk/task_schema.py` 与 `harness_sdk/task_parser.py`，不要污染其他模块。
2. Markdown frontmatter 解析优先用已有 `PyYAML` + 简单字符串切分，避免引入新依赖。
3. `completed` 状态必须兼容，但在 `--strict` 模式下标记为非法。
4. `graph_delta` 校验只检查文件是否存在，不检查图谱内容。
5. 测试必须覆盖：合法任务单、非法状态、缺失 graph_delta、批量目录扫描。
6. 新增测试 `tests/test_task_schema.py` 与 `tests/test_task_parser.py`。

---

## 实现备忘

- 新增 `harness_sdk/task_schema.py`：Pydantic 任务单模型与校验器。
- 新增 `harness_sdk/task_parser.py`：Markdown frontmatter / 验收项 / 失败路径表格解析。
- CLI 新增 `harness-probe task validate` 子命令。
- 新增 `docs/_tech_graph/92_task_schema.graph.yaml` 描述任务单解析到 verify 与 ops-desk 的依赖。
- 更新 `CHANGELOG.md`。

---

## 测试策略

`required`。任务单是 Harness 任务系统的核心契约，必须有可失败测试覆盖：
- Pydantic 模型校验（合法与非法状态）
- Markdown 解析器（frontmatter、验收项、失败路径表格）
- CLI `task validate` 返回码与输出格式
- 目录批量扫描与 `--strict` 模式

---

## 失败路径

| 触发条件 | 系统行为 | 是否可重试 | 用户可见类型 |
| --- | --- | --- | --- |
| 任务单 YAML frontmatter 解析失败 | `task validate` 报错，指出文件 | 修正后重试 | 文件级错误 |
| 缺少必填字段 | 列出缺失字段 | 修正后重试 | 字段级错误 |
| `status` 不合法 | 列出允许值 | 修正后重试 | 枚举错误 |
| `blocks_hats` 不是整数列表 | 列出类型错误 | 修正后重试 | 类型错误 |
| `graph_delta` 路径不存在 | 列出缺失文件 | 补图后重试 | 文件缺失 |
| `--strict` 模式下使用 `completed` | 标记为非法，建议使用 `approved` | 修正后重试 | 兼容性警告升级 |

---

## 给 Cursor

- 只新增 `harness_sdk/task_schema.py`、`harness_sdk/task_parser.py` 和 CLI 子命令，不动其他业务逻辑。
- 保持现有任务单文件不动，用测试中的临时文件覆盖非法路径。
- 所有新增测试必须真实通过，禁止伪造结果。
- 输出格式与现有 CLI（如 `config validate`）保持一致：默认 markdown 表格，可选 `--format json`。
