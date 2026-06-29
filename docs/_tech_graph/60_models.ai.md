# 60_models · Pydantic 数据模型

## nodes

```yaml
- id: MODELS
  label: "models.py"
  kind: data
  module_id: MODELS
  depends_on: []
  entry_points:
    - "GraphNode"
    - "GraphEdge"
    - "TechGraph"
    - "AcceptanceContract"
    - "HumanGate"
    - "HarnessTask"
    - "WikiEntry"
    - "SubgraphResult"
    - "CompiledPrompt"
    - "TaskRunNode"
    - "TaskRunGraph"
    - "BlockedError"
```

## edges

```yaml
# MODELS has no internal deps; consumed by all other modules
```

## 文件

- `src/models.py`
