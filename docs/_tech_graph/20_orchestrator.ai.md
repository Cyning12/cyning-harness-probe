# 20_orchestrator · HarnessProbeCore

## nodes

```yaml
- id: ORCHESTRATOR
  label: "HarnessProbeCore"
  kind: service
  module_id: ORCHESTRATOR
  depends_on: [BUILDER, COMPILER, GRAPH_LOADER]
  entry_points:
    - "gate_scan"
    - "pre_spawn_verify"
    - "run_task"
```

## edges

```yaml
- from: ORCHESTRATOR
  to: BUILDER
  mark: "->"
  type: depends_on
  label: "run_task → build_hat_prompt × hats"
- from: ORCHESTRATOR
  to: COMPILER
  mark: "->"
  type: depends_on
  label: "retrieve_wiki / load_wiki_stub"
- from: ORCHESTRATOR
  to: GRAPH_LOADER
  mark: "->"
  type: depends_on
  label: "load_graph / query_subgraph"
```

## 文件

- `src/orchestrator.py`
