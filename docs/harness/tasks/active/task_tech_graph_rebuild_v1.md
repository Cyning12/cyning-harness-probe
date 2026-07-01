# task_tech_graph_rebuild_v1

## Harness 元信息

| 字段 | 值 |
| --- | --- |
| **track** | `refactor` |
| **lightweight_task** | `yes` |
| **module_id** | `TECH-GRAPH` |
| **graph_delta** | `none`（本任务为文档重构，无单一 graph_delta 文件） |
| **test_strategy** | `recommended` |
| **freeze_id** | `HARNESS-PROBE-GRAPH-V3` |
| **gates_before_code** | `["human_gate"]` |
| **orchestration** | Hermes 直接执行 |
| **git_branch** | `task/tech-graph-rebuild-v1` |
| **worktree_root** | `harness-probe/` |
| **task_slug** | `tech-graph-rebuild-v1` |
| **status** | `draft` |
| **target_version** | `v0.7.1` |
| **parent_epic** | 无 |
| **date** | `2026-06-30` |

### 人工闸 `human_gate`

| human_gate_id | status | blocks_hats | 说明 |
| --- | --- | --- | --- |
| HG-TASK-DRAFT | `approved` | 30 | 任务单定稿 |
| HG-AUDIT-R1 | `approved` | 30 | 轻量文档重构，跳过 R1 审计 |
| HG-EXEC-AUTH | `approved` | 30 | 授权整理图谱 |

## 背景与目标

当前 `docs/_tech_graph/` 存在以下问题：

1. 残留大量 `*.ai.md` 文件，与 `.md` 双轨并行但内容重复/过时
2. `.graph.yaml` 源文件未反映 v0.7 新增模块：`safety.py`、`executor.py`、MCP tools
3. `graph.json` 中的节点/边未与安全执行器、真实执行器、执行日志等新能力对齐
4. 缺少顶层总图 `00_main.md`，无法一眼看清 harness-probe 全貌
5. 缺少 `01_struct.md` 数据结构说明与 `02_version.md` 版本时间线

本任务目标：

- 删除所有 `*.ai.md`
- 基于当前代码重新整理 `.graph.yaml` 源文件
- 重新生成人类可读的 `.md` 文档
- 重新导出 `graph.json`
- 补齐 `00_main.md`、`01_struct.md`、`02_version.md`
- 更新 `README.md` 与 `99_mermaid_protocol.md`

## 范围

- `docs/_tech_graph/*.ai.md`：删除
- `docs/_tech_graph/*.graph.yaml`：重写/新增
- `docs/_tech_graph/*.md`：由脚本重新生成
- `docs/_tech_graph/graph.json`：重新导出
- `docs/_tech_graph/00_main.md`：新增顶层总图
- `docs/_tech_graph/01_struct.md`：新增数据结构说明
- `docs/_tech_graph/02_version.md`：新增版本时间线
- `docs/_tech_graph/99_mermaid_protocol.md`：更新维护协议
- `docs/_tech_graph/README.md`：更新索引
- `harness_probe/cli.py` 中 `graph-query` 默认图路径无需修改

## 非范围

- 不改业务代码逻辑
- 不改测试
- 不改 `cyning-harness` 产品包
- 不新增 `.ai.md` 文件

## 依赖

- v0.7.0 已合并至 `main`
- `docs/_tech_graph/scripts/graph_yaml_compile.py` 已存在
- `docs/_tech_graph/scripts/graph_json_export.py` 已存在

## 验收标准

- [ ] 所有 `*.ai.md` 已删除
- [ ] `.graph.yaml` 覆盖 CLI、RUNNER、COMPILER、BUILDER、GRAPH、MODELS、IO、EXTERNAL、SAFETY、EXECUTOR、MCP
- [ ] `.md` 由脚本重新生成，人类可读，含 Mermaid 图与节点/边表格
- [ ] `00_main.md` 展示顶层总图
- [ ] `01_struct.md` 说明核心数据模型
- [ ] `02_version.md` 展示 v0.1 → v0.7 时间线
- [ ] `graph.json` 成功导出且 `graph-query --node CLI --depth 3` 可运行
- [ ] `pytest tests/ -q` 仍全绿
- [ ] `ruff check` 与 `mypy harness_sdk` 仍通过

## 失败路径

| ID | 触发条件 | 系统行为 | 可重试 | 用户可见 |
| --- | --- | --- | --- | --- |
| G1 | `.graph.yaml` 语法错误 | 编译脚本报错，不生成 `.md` | 是 | 提示 YAML 行号 |
| G2 | 节点 ID 重复 | `graph_json_export.py` 去重跳过 | 否 | 警告日志 |
| G3 | 边指向不存在的节点 | `graph-query` 仍可运行，子图不完整 | 否 | 需人工检查 |

## 实现备忘

- 删除 `docs/_tech_graph/*.ai.md`
- 新增/重写 `.graph.yaml`：
  - `00_main.graph.yaml`：顶层总图
  - `01_struct.graph.yaml`：核心数据结构
  - `02_version.graph.yaml`：版本时间线
  - `10_cli.graph.yaml`、`20_runner.graph.yaml`、`30_compiler.graph.yaml`、`40_builder.graph.yaml`、`50_graph.graph.yaml`、`60_models.graph.yaml`、`70_io.graph.yaml`、`80_external.graph.yaml`、`85_mcp.graph.yaml`、`90_executor.graph.yaml`
- 运行 `graph_yaml_compile.py` 重新生成 13 个 `.md`
- 运行 `graph_json_export.py` 重新生成 `graph.json`
- 更新 `README.md` 与 `99_mermaid_protocol.md`

### 自检结论（执行者）

- `docs/_tech_graph/*.ai.md`：已清空
- `graph-query --node CLI --depth 3`：成功，21 nodes
- `pytest tests/ -q`：49 passed
- `ruff check harness_sdk tests harness_probe harness_mcp`：All checks passed
- `mypy harness_sdk --ignore-missing-imports`：Success

## 测试策略

`recommended`。图谱整理以文档与脚本为主，关键验证是 `graph-query` 可运行与 CI 仍绿。

## 修订记录

| 版本 | 日期 | 说明 |
| --- | --- | --- |
| v1 | 2026-06-30 | 初稿 |
