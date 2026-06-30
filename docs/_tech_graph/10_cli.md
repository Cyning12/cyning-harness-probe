---
description: "argparse \u547D\u4EE4\u5206\u53D1\u4E0E\u53C2\u6570\u89E3\u6790"
generated_from: 10_cli.graph.yaml
generator: docs/_tech_graph/scripts/graph_yaml_compile.py
graph_id: 10_cli
title: "probe CLI \u5165\u53E3"
version: '2026-06-30'
---

# probe CLI 入口

> argparse 命令分发与参数解析

> **源文件**：`10_cli.graph.yaml` · 由 `docs/_tech_graph/scripts/graph_yaml_compile.py` 生成 · 请勿直接手写本文件

```mermaid
flowchart TD
    CLI[["probe CLI"]]
    RUNNER[["TaskRunner"]]
    COMPILER[["compiler.py"]]
    GRAPH[["graph.py"]]
    IO[["io.py"]]
    CLI --"cmd_run/run_sequence"--> RUNNER
    CLI --"cmd_verify"--> COMPILER
    CLI --"cmd_graph_query / cmd_watch"--> GRAPH
    CLI --"load_graph / parse_task_markdown"--> IO
    %% 锚点：见 YAML 源 edges[].anchors
```

## Nodes

| ID | Label | Kind |
|----|-------|------|
| CLI | probe CLI | entry |
| RUNNER | TaskRunner | service |
| COMPILER | compiler.py | service |
| GRAPH | graph.py | service |
| IO | io.py | service |

## Edges

| From | To | Label | Type |
|------|----|-------|------|
| CLI | RUNNER | cmd_run/run_sequence |  |
| CLI | COMPILER | cmd_verify |  |
| CLI | GRAPH | cmd_graph_query / cmd_watch |  |
| CLI | IO | load_graph / parse_task_markdown |  |
