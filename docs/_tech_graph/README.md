# 技术图谱 · harness-probe

> **用途**：Agent 改代码前 query 子图（depth=2），了解模块间依赖。  
> **真值**：各 `.ai.md` 为手写源；`graph.json` 为导出产物。  
> **导出**：当前手工维护（模块少且稳定），Phase 2 引入自动导出。

## 模块

| # | 文件 | 模块 | 职责 |
|---|------|------|------|
| 10 | `10_cli.ai.md` | CLI | argparse + 命令分发 |
| 20 | `20_orchestrator.ai.md` | ORCHESTRATOR | gate_scan + run_task |
| 30 | `30_compiler.ai.md` | COMPILER | task parser + contract |
| 40 | `40_builder.ai.md` | BUILDER | Prompt 三段式组装 |
| 50 | `50_graph_loader.ai.md` | GRAPH_LOADER | graph_v2 加载 + BFS |
| 60 | `60_models.ai.md` | MODELS | Pydantic 数据模型 |
| 70 | `70_external.ai.md` | — | @cyning/harness + 工作区 |

## 子图查询示例

```bash
# CLI 及其直接依赖
python -m src.probe graph-query --graph docs/_tech_graph/graph.json --node CLI --depth 2

# orchestrator 上下游
python -m src.probe graph-query --graph docs/_tech_graph/graph.json --node ORCHESTRATOR --depth 2
```
