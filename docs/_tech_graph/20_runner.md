---
description: "\u7EAF\u903B\u8F91\u6267\u884C\u5668\uFF1Agate_scan\u3001pre_spawn_verify\u3001\
  run_sequence"
generated_from: 20_runner.graph.yaml
generator: docs/_tech_graph/scripts/graph_yaml_compile.py
graph_id: 20_runner
title: "TaskRunner \u591A\u5E3D\u6267\u884C\u7F16\u6392"
version: '2026-06-30'
---

# TaskRunner 多帽执行编排

> 纯逻辑执行器：gate_scan、pre_spawn_verify、run_sequence

> **源文件**：`20_runner.graph.yaml` · 由 `docs/_tech_graph/scripts/graph_yaml_compile.py` 生成 · 请勿直接手写本文件

```mermaid
flowchart TD
    RUNNER[["TaskRunner"]]
    BUILDER[["builder.py"]]
    COMPILER[["compiler.py"]]
    GRAPH[["graph.py"]]
    EXECUTOR[["executor.py"]]
    MODELS[["models.py"]]
    RUNNER --"build_hat_prompt × hats"--> BUILDER
    RUNNER --"retrieve_wiki"--> COMPILER
    RUNNER --"query_subgraph"--> GRAPH
    RUNNER --"真实执行 verify 命令"--> EXECUTOR
    BUILDER --"format_contract_table / format_wiki_context"--> COMPILER
    COMPILER --"AcceptanceContract / HumanGate / HarnessTask"--> MODELS
    GRAPH --"TechGraph / GraphNode / GraphEdge / SubgraphResult"--> MODELS
    EXECUTOR --"ExecutionResult"--> MODELS
    %% 锚点：见 YAML 源 edges[].anchors
```

## Nodes

| ID | Label | Kind |
|----|-------|------|
| RUNNER | TaskRunner | service |
| BUILDER | builder.py | service |
| COMPILER | compiler.py | service |
| GRAPH | graph.py | service |
| EXECUTOR | executor.py | service |
| MODELS | models.py | data |

## Edges

| From | To | Label | Type |
|------|----|-------|------|
| RUNNER | BUILDER | build_hat_prompt × hats |  |
| RUNNER | COMPILER | retrieve_wiki |  |
| RUNNER | GRAPH | query_subgraph |  |
| RUNNER | EXECUTOR | 真实执行 verify 命令 |  |
| BUILDER | COMPILER | format_contract_table / format_wiki_context |  |
| COMPILER | MODELS | AcceptanceContract / HumanGate / HarnessTask |  |
| GRAPH | MODELS | TechGraph / GraphNode / GraphEdge / SubgraphResult |  |
| EXECUTOR | MODELS | ExecutionResult |  |
