---
description: "\u52A0\u8F7D graph.json\uFF0C\u63D0\u4F9B query_subgraph BFS \u4E0E\
  \ Mermaid \u6E32\u67D3"
generated_from: 50_graph.graph.yaml
generator: docs/_tech_graph/scripts/graph_yaml_compile.py
graph_id: 50_graph
title: "graph_v2 \u52A0\u8F7D\u4E0E\u5B50\u56FE\u67E5\u8BE2"
version: '2026-06-30'
---

# graph_v2 加载与子图查询

> 加载 graph.json，提供 query_subgraph BFS 与 Mermaid 渲染

> **源文件**：`50_graph.graph.yaml` · 由 `docs/_tech_graph/scripts/graph_yaml_compile.py` 生成 · 请勿直接手写本文件

```mermaid
flowchart TD
    GRAPH[["graph.py"]]
    MODELS[["models.py"]]
    GRAPH_JSON[["docs/_tech_graph/graph.json"]]
    GRAPH --"load_graph"--> GRAPH_JSON
    GRAPH --"TechGraph / GraphNode / GraphEdge / SubgraphResult"--> MODELS
    %% 锚点：见 YAML 源 edges[].anchors
```

## Nodes

| ID | Label | Kind |
|----|-------|------|
| GRAPH | graph.py | service |
| MODELS | models.py | data |
| GRAPH_JSON | docs/_tech_graph/graph.json | storage |

## Edges

| From | To | Label | Type |
|------|----|-------|------|
| GRAPH | GRAPH_JSON | load_graph |  |
| GRAPH | MODELS | TechGraph / GraphNode / GraphEdge / SubgraphResult |  |
