# Harness Probe

> **Harness 探针工程** — 验证 L0 图谱编译 + L1 验收合约 + L2 冷记忆 + KV-Cache 友好 Prompt 组装。  
> **不是** Agent 产品 Runtime；dry-run 为主，无真实 LLM 调用。  
> **当前版本**：**v0.7** · 见 [`CHANGELOG.md`](./CHANGELOG.md)

**仓库**：https://github.com/Cyning12/cyning-harness-probe · `git@github.com:Cyning12/cyning-harness-probe.git`

## 快速开始

```bash
cd harness-probe
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 编译全帽链 Prompt（dry-run）
python -m harness_probe.cli compile --task data/tasks/sample_task.md --entry RAG --hat 10-spec,20-review,30,40
python -m harness_probe.cli compile --task data/tasks/sample_task.md --entry RAG --hat 50-reinspect --mode global

# L0 子图查询
python -m harness_probe.cli graph-query --node RAG --depth 2

# PRE_SPAWN_VERIFY 人闸校验
python -m harness_probe.cli verify --task data/tasks/sample_task.md

# 模拟执行（30→40，默认 mock，与 v0.5 行为一致）
python -m harness_probe.cli run --from-hat 30 --to-hat 40

# 真实执行 contract.verify（需显式授权 --executor real）
python -m harness_probe.cli run --executor real --from-hat 30 --to-hat 40

# dry-run 模式（不执行，仅预览）
python -m harness_probe.cli run --executor real --dry-run --from-hat 30 --to-hat 40

# 安全模式：whitelist（默认）/ audit / unsafe
python -m harness_probe.cli run --executor real --safety-mode audit --from-hat 30 --to-hat 40

# 失败时重跑 2 次
python -m harness_probe.cli run --executor real --max-retries 2 --from-hat 30 --to-hat 40

# 指定工作目录
python -m harness_probe.cli run --executor real --cwd . --from-hat 30 --to-hat 40

# freeze_id 漂移检测
python -m harness_probe.cli watch --once --entry RAG

# 测试
pytest tests/ -q
```

## 目录结构

```text
harness-probe/
├── harness_sdk/          # 无副作用 SDK（可 pip 安装）
│   ├── models.py
│   ├── compiler.py
│   ├── builder.py
│   ├── graph.py
│   ├── runner.py
│   ├── executor.py
│   └── safety.py
├── harness_probe/        # CLI + IO 层
│   ├── cli.py
│   ├── io.py
│   └── rendering.py
├── harness_mcp/          # MCP Server（Phase 3，可选依赖 [mcp]）
│   └── ...
├── tests/
│   ├── test_sdk_*.py
│   └── test_cli.py
└── pyproject.toml
```

## 输出

| 路径 | 含义 |
| --- | --- |
| `outputs/prompt_<session>_hat30.md` | 某帽完整 Subagent Prompt |
| `outputs/task_run_<session>.json` | **L1.5** 任务执行实例图 |
| `outputs/execution_log_<session>.jsonl` | 执行/拦截事件日志（v0.7+） |

## 使用 Ink 全量图谱

```bash
python -m harness_probe.cli compile \
  --graph ../ai-ink-brain-api-python/docs/_tech_graph/graph.json \
  --task data/tasks/sample_task.md \
  --entry RAG
```

## 作为 SDK 使用

```python
from harness_sdk import TaskRunner, build_hat_prompt
from harness_probe.io import load_graph, parse_task_markdown, load_wiki_stub

graph = load_graph("data/graph/sample_graph_v2.json")
task = parse_task_markdown("data/tasks/sample_task.md")
wiki = load_wiki_stub("data/wiki/syntheses_stub.json")

runner = TaskRunner(task, graph, wiki)
run_graph = runner.run_sequence(from_hat="30", to_hat="40")
print(run_graph.status)
```

## MCP Server（可选）

```bash
pip install -e ".[mcp]"
python -m harness_mcp.server
```

提供 Tool：`probe_compile` / `probe_run` / `probe_audit` / `probe_verify`  
提供 Resource：`harness://freeze_id/current`

## 文档

- [方法论定位（推荐阅读）](docs/METHODOLOGY_v1_zh.md)
- [架构 v1](docs/ARCHITECTURE_v1_zh.md)
- [SDK 重构方案](docs/PLAN_SDK_REFACTOR_v1_zh.md)
- [MCP Server 方案](docs/PLAN_MCP_SERVER_v1_zh.md)

## 在方法论中的位置

Probe 是 **完整 Harness 的编译链子集**（非 Agent 产品、非 Runtime）。未来可并入 Agent 产品的 **Harness SDK**（`compile_context` + contract + L1.5）。详见 [`docs/METHODOLOGY_v1_zh.md`](docs/METHODOLOGY_v1_zh.md)。

## 设计哲学

**大脑（LLM）负责推理，Harness（Core）负责托底。**

```text
L0 静态图（仓库）  +  L1.5 动态轨迹（会话）  +  L1 合约（task）  +  L2 摘要（Wiki）
         ↓                      ↓
    graph_query              task_run JSON
         ↓                      ↓
              Subagent Prompt（三段式）
```

## License

MIT · 源自 Ink 工作区 Harness 实验，独立维护
