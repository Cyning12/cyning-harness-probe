# 10_cli · probe CLI 入口

## nodes

```yaml
- id: CLI
  label: "probe CLI"
  kind: entry
  module_id: CLI
  depends_on: [ORCHESTRATOR, GRAPH_LOADER, COMPILER]
  entry_points:
    - "python -m src.probe compile"
    - "python -m src.probe verify"
    - "python -m src.probe run"
    - "python -m src.probe watch"
    - "python -m src.probe graph-query"
```

## edges

```yaml
- from: CLI
  to: ORCHESTRATOR
  mark: "->"
  type: depends_on
  label: "cmd_run → HarnessProbeCore.run_task"
- from: CLI
  to: COMPILER
  mark: "->"
  type: depends_on
  label: "cmd_verify → validate_task_markdown"
- from: CLI
  to: GRAPH_LOADER
  mark: "->"
  type: depends_on
  label: "cmd_graph_query / cmd_watch → load_graph / query_subgraph"
```

## 文件

- `src/probe.py`
