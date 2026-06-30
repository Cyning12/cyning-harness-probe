---
description: "graph_v2 \u52A0\u8F7D\u3001BFS \u88C1\u526A\u3001Mermaid \u751F\u6210"
generated_from: 50_graph.graph.yaml
generator: docs/_tech_graph/scripts/graph_yaml_compile.py
graph_id: 50_graph
title: "L0 \u56FE\u8C31\u52A0\u8F7D\u4E0E\u5B50\u56FE\u67E5\u8BE2"
version: '2026-06-30'
---

# L0 图谱加载与子图查询

> graph_v2 加载、BFS 裁剪、Mermaid 生成

> **源文件**：`50_graph.graph.yaml` · 由 `docs/_tech_graph/scripts/graph_yaml_compile.py` 生成 · 请勿直接手写本文件

```mermaid
flowchart TD
    GRAPH[["graph.py"]]
    MODELS[["models.py"]]
    GRAPH --"TechGraph / GraphNode / GraphEdge / SubgraphResult"--> MODELS
    %% 锚点：见 YAML 源 edges[].anchors
```

## Nodes

| ID | Label | Kind |
|----|-------|------|
| GRAPH | graph.py | service |
| MODELS | models.py | data |

## Edges

| From | To | Label | Type |
|------|----|-------|------|
| GRAPH | MODELS | TechGraph / GraphNode / GraphEdge / SubgraphResult |  |
