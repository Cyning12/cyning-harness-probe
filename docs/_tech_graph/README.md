# 技术图谱 · harness-probe

> **用途**：Agent 改代码前 query 子图（depth=2），了解模块间依赖。  
> **真值**：各 `.graph.yaml` 为手写源；`.md` 由脚本生成；`graph.json` 为导出产物。  
> **导出**：
>   - `python docs/_tech_graph/scripts/graph_yaml_compile.py` → 生成 `.md`
>   - `python docs/_tech_graph/scripts/graph_json_export.py` → 生成 `graph.json`

## 模块

| # | 源文件 | 模块 | 职责 |
|---|--------|------|------|
| 10 | `10_cli.graph.yaml` | CLI | argparse + 命令分发 |
| 20 | `20_runner.graph.yaml` | RUNNER | TaskRunner 多帽执行编排 |
| 30 | `30_compiler.graph.yaml` | COMPILER | task parser + contract |
| 40 | `40_builder.graph.yaml` | BUILDER | Prompt 三段式组装 |
| 50 | `50_graph.graph.yaml` | GRAPH | graph_v2 加载 + BFS |
| 60 | `60_models.graph.yaml` | MODELS | Pydantic 数据模型 |
| 70 | `70_io.graph.yaml` | IO | 文件 IO + 渲染 |
| 80 | `80_external.graph.yaml` | — | @cyning/harness + 工作区 |

## 子图查询示例

```bash
# CLI 及其直接依赖
python -m harness_probe.cli graph-query --graph docs/_tech_graph/graph.json --node CLI --depth 2

# runner 上下游
python -m harness_probe.cli graph-query --graph docs/_tech_graph/graph.json --node RUNNER --depth 2
```

## 维护

1. 修改对应 `.graph.yaml`
2. 运行 `python docs/_tech_graph/scripts/graph_yaml_compile.py` 重新生成 `.md`
3. 运行 `python docs/_tech_graph/scripts/graph_json_export.py` 重新生成 `graph.json`
4. 运行 `python -m harness_probe.cli graph-query ...` 验证子图完整性
