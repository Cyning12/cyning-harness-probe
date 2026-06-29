# 50_graph_loader · L0 图谱加载与子图查询

## nodes

```yaml
- id: GRAPH_LOADER
  label: "graph_loader.py"
  kind: service
  module_id: GRAPH_LOADER
  depends_on: [MODELS]
  entry_points:
    - "load_graph"
    - "query_subgraph"
    - "subgraph_to_mermaid"
```

## edges

```yaml
- from: GRAPH_LOADER
  to: MODELS
  mark: "->"
  type: depends_on
  label: "TechGraph / GraphNode / GraphEdge / SubgraphResult"
```

## 文件

- `src/graph_loader.py`
