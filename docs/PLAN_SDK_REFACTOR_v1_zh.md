# SDK 重构方案 · 从 `src/` 到 `harness_sdk/`（v1）

| 项 | 内容 |
| --- | --- |
| **状态** | `planning` |
| **版本** | v1 |
| **日期** | 2026-06-29 |
| **目标** | 将 Probe CLI 中的“计算逻辑”与“IO/CLI 搬运逻辑”分离，形成可 pip 安装的 `harness_sdk` |

---

## 1. 重构原则

### 1.1 无副作用边界

**SDK 层（纯函数 / 纯对象）**：

- 不读文件
- 不写文件
- 不 print
- 不访问环境变量
- 输入输出均为 Python 对象（dict、dataclass、Pydantic Model）

**CLI 层（IO / 搬运）**：

- 读 task.md / graph.json / wiki.json
- 写 `outputs/prompt_*.md` / `task_run_*.json`
- 解析命令行参数
- 打印人类可读输出
- 捕获异常并转换 exit code

### 1.2 渐进策略

1. 先新建 `harness_sdk/` 目录，把纯函数迁移过去。
2. `src/` 暂时作为 `harness_sdk` 的薄 wrapper，保证现有 CLI 不中断。
3. 单测先在 `tests/` 中直接测 SDK；CLI 测试只测参数解析和 exit code。
4. 验证稳定后，再将 `src/` 重命名为 `harness_probe/` 或直接删除，CLI 入口改为 `harness_sdk/cli.py`。

---

## 2. 当前代码职责分析

### 2.1 `src/compiler.py`

| 函数 | 当前职责 | 副作用 | 归属 |
| --- | --- | --- | --- |
| `parse_task_markdown` | 读文件 + 解析 task 元信息 + contract + human_gate | **读文件** | **CLI 层** |
| `compile_contracts_from_task` | 从 task 文本解析 failure_paths 表 → AcceptanceContract | 无 | **SDK** |
| `validate_human_gate_rules` | 校验 human_gate 规则 | 无 | **SDK** |
| `validate_task_markdown` | 读文件 + 校验 | **读文件** | **CLI 层** |
| `_extract_section` | 字符串切片 | 无 | **SDK** |
| `_suggest_verify` | 根据 trigger/expected 推荐 verify 命令 | 无 | **SDK** |
| `parse_human_gates` | 从 task 文本解析 human_gate 表 | 无 | **SDK** |
| `load_wiki_stub` | 读 wiki JSON | **读文件** | **CLI 层** |
| `retrieve_wiki` | 从 wiki 列表检索 Top-K | 无 | **SDK** |
| `format_wiki_context` | 格式化 wiki 摘要块 | 无 | **SDK** |
| `format_contract_table` | 格式化 AcceptanceContract 表 | 无 | **SDK** |

### 2.2 `src/builder.py`

| 函数 | 当前职责 | 副作用 | 归属 |
| --- | --- | --- | --- |
| `build_subagent_prompt` | 组装 static / semi_static / dynamic 三段 Prompt | 无 | **SDK** |
| `print_cache_boundary` | 用 rich 打印 Prompt 边界 | **print**、依赖 rich | **CLI 层** |

### 2.3 `src/graph_loader.py`

| 函数 | 当前职责 | 副作用 | 归属 |
| --- | --- | --- | --- |
| `load_graph` | 读 graph.json → TechGraph | **读文件** | **CLI 层** |
| `query_subgraph` | BFS 裁剪子图 | 无 | **SDK** |
| `_adjacency` | 构建邻接表 | 无 | **SDK** |
| `subgraph_to_mermaid` | 子图 → Mermaid | 无 | **SDK** |

### 2.4 `src/orchestrator.py`

| 函数/类 | 当前职责 | 副作用 | 归属 |
| --- | --- | --- | --- |
| `HarnessProbeCore.gate_scan` | 扫描 human_gate 阻塞 | 无 | **SDK** |
| `HarnessProbeCore.pre_spawn_verify` | 校验 contract 非空 / ≤15 行 | 无 | **SDK** |
| `HarnessProbeCore.run_task` | 串行跑多帽 + 写 Prompt + 写 task_run JSON | **写文件**、print | **混合**：计算逻辑归 SDK，IO 归 CLI |
| `HarnessProbeCore._mock_subagent_result` | Mock 执行结果 | 无 | **SDK** |
| `HarnessProbeCore._persist_run_graph` | 写 task_run JSON | **写文件** | **CLI 层** |
| `HarnessProbeCore.propose_graph_evolution_note` | 生成 PR 提案文本 | 无 | **SDK** |

### 2.5 `src/models.py`

| 类 | 归属 |
| --- | --- |
| `GraphAnchor`、`GraphNode`、`GraphEdge`、`TechGraph` | **SDK** |
| `AcceptanceContract`、`HumanGate`、`HarnessTask` | **SDK** |
| `WikiEntry`、`SubgraphResult` | **SDK** |
| `RunNodeStatus`、`TaskRunNode`、`TaskRunGraph` | **SDK** |
| `BlockedError` | **SDK** |

### 2.6 `src/probe.py`

全部归属 **CLI 层**。

---

## 3. 新目录树

```text
harness-probe/
├── harness_sdk/                      # 核心库（纯函数 / 数据类）
│   ├── __init__.py
│   ├── models.py                     # 全部 Pydantic / dataclass 模型
│   ├── exceptions.py                 # BlockedError 等异常
│   ├── compiler.py                   # compile_contracts, parse_human_gates, validate_human_gate_rules, retrieve_wiki, format_*
│   ├── builder.py                    # build_subagent_prompt, build_hat_prompt
│   ├── graph.py                      # query_subgraph, subgraph_to_mermaid
│   ├── runner.py                     # HatRunner / TaskRunner 纯逻辑（不读写文件）
│   └── orchestrator.py               # gate_scan, pre_spawn_verify 纯校验逻辑
│
├── harness_probe/                    # CLI 与 IO 层（未来名称）
│   ├── __init__.py
│   ├── cli.py                        # argparse + 命令分发
│   ├── io.py                         # load_graph, load_wiki_stub, parse_task_markdown, persist_prompt, persist_run_graph
│   ├── rendering.py                  # print_cache_boundary, console 输出
│   └── main.py                       # 入口：__main__ 调用 cli.main
│
├── tests/
│   ├── test_sdk_compiler.py          # 纯 SDK 测试
│   ├── test_sdk_builder.py           # Prompt 组装测试
│   ├── test_sdk_graph.py             # 子图查询测试
│   ├── test_sdk_runner.py            # runner 逻辑测试
│   └── test_cli.py                   # CLI 参数与 exit code 测试
│
├── pyproject.toml                    # 新增：定义 harness-probe CLI + harness_sdk 包
├── CHANGELOG.md
└── README.md
```

---

## 4. 关键接口设计

### 4.1 SDK 公共 API

```python
# harness_sdk/__init__.py
from harness_sdk.compiler import (
    compile_contracts_from_task,
    parse_human_gates,
    validate_human_gate_rules,
    retrieve_wiki,
    format_contract_table,
    format_wiki_context,
)
from harness_sdk.builder import build_subagent_prompt, build_hat_prompt
from harness_sdk.graph import query_subgraph, subgraph_to_mermaid
from harness_sdk.runner import HatRunner, TaskRunner
from harness_sdk.orchestrator import gate_scan, pre_spawn_verify
from harness_sdk.models import (
    AcceptanceContract,
    HumanGate,
    HarnessTask,
    TechGraph,
    SubgraphResult,
    TaskRunGraph,
)
from harness_sdk.exceptions import BlockedError
```

### 4.2 `build_hat_prompt` 签名

```python
def build_hat_prompt(
    hat: str,
    task: HarnessTask,
    graph: TechGraph,
    subgraph: SubgraphResult,
    wiki_entries: list[WikiEntry],
    handoff_summary: str = "",
) -> CompiledPrompt:
    """按帽子生成三段式 Prompt。

    Args:
        hat: 帽子编号，如 "10-spec", "10-task", "20-review", "30", "40", "50-reinspect"
        task: 解析后的 task 对象
        graph: 完整图谱
        subgraph: 已裁剪子图
        wiki_entries: L2 摘要列表
        handoff_summary: 上一帽摘要
    """
```

### 4.3 `TaskRunner` 签名（纯逻辑）

```python
class TaskRunner:
    def __init__(
        self,
        task: HarnessTask,
        graph: TechGraph,
        wiki_entries: list[WikiEntry],
        mock_executor: Callable[[HarnessTask, str], dict[str, str]] | None = None,
    ):
        ...

    def run_sequence(
        self,
        from_hat: str,
        to_hat: str,
    ) -> TaskRunGraph:
        """生成运行计划，调用 mock_executor / 真实 executor，返回 TaskRunGraph。

        不读写文件。
        """
```

### 4.4 IO 层函数

```python
# harness_probe/io.py
from pathlib import Path
import json
from harness_sdk.models import TechGraph, HarnessTask, TaskRunGraph
from harness_sdk.compiler import compile_contracts_from_task, parse_human_gates


def load_graph(path: Path) -> TechGraph:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return TechGraph.model_validate(raw)


def parse_task_markdown(path: Path, dynamic_query: str = "") -> HarnessTask:
    text = path.read_text(encoding="utf-8")
    # 解析 meta、contracts、gates、entry_node
    ...


def persist_prompt(path: Path, compiled: CompiledPrompt) -> None:
    path.write_text(compiled.full_text, encoding="utf-8")


def persist_run_graph(path: Path, run_graph: TaskRunGraph) -> None:
    path.write_text(run_graph.model_dump_json(indent=2), encoding="utf-8")
```

---

## 5. 重构步骤

### Step 1：新建 `harness_sdk/` 并迁移模型

- 复制 `src/models.py` → `harness_sdk/models.py`
- 复制 `BlockedError` → `harness_sdk/exceptions.py`
- 运行 `pytest tests/test_sdk_models.py` 确保模型测试通过

### Step 2：迁移 compiler / builder / graph

- 纯函数迁移至 `harness_sdk/compiler.py`、`harness_sdk/builder.py`、`harness_sdk/graph.py`
- 保留 `src/compiler.py` 等文件，但改为从 `harness_sdk` import 并加 `@deprecated` 注释
- 运行 `pytest tests/ -q` 确保 CLI 仍通过

### Step 3：拆分 orchestrator

- 将 `HarnessProbeCore` 中无 IO 的方法抽出为 `harness_sdk/orchestrator.py` 的纯函数
- 剩余带 IO 的逻辑放入 `harness_probe/io.py` + `harness_probe/runner_cli.py`

### Step 4：CLI 入口迁移

- 新建 `harness_probe/cli.py`，调用 SDK + IO
- `pyproject.toml` 添加：

```toml
[project]
name = "harness-probe"
version = "0.2.0"
dependencies = ["pydantic", "pyyaml", "rich"]

[project.scripts]
harness-probe = "harness_probe.cli:main"
```

### Step 5：删除旧 `src/`

- 验证 `python -m harness_probe.cli compile ...` 与旧 `python -m src.probe compile ...` 等价
- 删除 `src/`
- 更新 README

---

## 6. 测试策略

| 测试层 | 覆盖目标 | 示例 |
| --- | --- | --- |
| SDK 单元测试 | 纯函数输入输出 | `test_sdk_compiler.py::test_compile_contracts` |
| SDK 集成测试 | 端到端编译链 | `test_sdk_builder.py::test_build_hat30_prompt` |
| CLI 测试 | 参数解析、文件落盘、exit code | `test_cli.py::test_compile_command_creates_prompt` |
| IO 隔离测试 | Mock 文件系统 | `test_io.py::test_load_graph_invalid_json` |

---

## 7. 风险与对策

| 风险 | 对策 |
| --- | --- |
| 重构期间 CLI 行为改变 | Step 2 保留旧 `src/` wrapper，双路径并行验证 |
| SDK 过度抽象导致接口不稳定 | 先满足当前 3 个 CLI 命令的需求，不预设过多扩展点 |
| 测试覆盖率下降 | 重构前记录基线覆盖率，重构后必须 ≥ 基线 |

---

## 给 Cursor

`harness_sdk`、无副作用、`src/` 重构、`pyproject.toml`、SDK / CLI 分层、`CompiledPrompt`
