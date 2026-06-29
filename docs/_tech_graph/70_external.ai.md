# 70_external · 外部依赖

## nodes

```yaml
- id: CYNING_HARNESS
  label: "@cyning/harness"
  kind: external
  module_id: CYNING_HARNESS
  depends_on: []
  entry_points:
    - "npx @cyning/harness verify"
    - "npx @cyning/harness init"
- id: WORKSPACE
  label: "Ink 工作区"
  kind: external
  module_id: WORKSPACE
  depends_on: []
  entry_points:
    - "docs/harness/prompts/PROMPT_cursor_task_chain_serial_v1.md"
    - "docs/harness/guides/COMPARISON_tech_graph_coding_wiki_graph_memory_v1_zh.md §2.2"
```

## edges

```yaml
- from: CLI
  to: CYNING_HARNESS
  mark: "..>"
  type: optional_depends_on
  label: "verify 命令可 shell out npx @cyning/harness verify"
- from: ORCHESTRATOR
  to: WORKSPACE
  mark: "..>"
  type: references
  label: "pre_spawn_verify / gate_scan 对齐 workspace PROMPT v1.1"
```

## 文件

- `package.json`（如将来添加）
- workspace: `Projects/docs/harness/`
