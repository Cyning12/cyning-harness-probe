---
description: "\u4ECE CLI \u5165\u53E3\u5230 SDK \u5404\u6A21\u5757\u3001MCP \u4E0E\
  \u5916\u90E8\u4F9D\u8D56\u7684\u5168\u5C40\u89C6\u56FE"
generated_from: 00_main.graph.yaml
generator: docs/_tech_graph/scripts/graph_yaml_compile.py
graph_id: 00_main
title: "harness-probe \u9876\u5C42\u603B\u56FE"
version: '2026-06-30'
---

# harness-probe 顶层总图

> 从 CLI 入口到 SDK 各模块、MCP 与外部依赖的全局视图

> **源文件**：`00_main.graph.yaml` · 由 `docs/_tech_graph/scripts/graph_yaml_compile.py` 生成 · 请勿直接手写本文件

```mermaid
flowchart TD
    CLI[["probe CLI"]]
    MCP[["MCP Server"]]
    RUNNER[["TaskRunner"]]
    BUILDER[["builder.py"]]
    COMPILER[["compiler.py"]]
    GRAPH[["graph.py"]]
    EXECUTOR[["executor.py"]]
    SAFETY[["safety.py"]]
    MODELS[["models.py"]]
    IO[["io.py"]]
    EXTERNAL[["@cyning/harness + 工作区"]]
    CLI --"cmd_run"--> RUNNER
    CLI --"cmd_graph_query / cmd_watch"--> GRAPH
    CLI --"load_graph / parse_task_markdown"--> IO
    MCP --"probe_run / probe_compile"--> RUNNER
    MCP --"probe_verify"--> IO
    RUNNER --"build_hat_prompt"--> BUILDER
    RUNNER --"retrieve_wiki / contract"--> COMPILER
    RUNNER --"query_subgraph"--> GRAPH
    RUNNER --"真实执行 verify 命令"--> EXECUTOR
    EXECUTOR --"CommandSafetyChecker.check"--> SAFETY
    BUILDER --"format_contract_table / format_wiki_context"--> COMPILER
    COMPILER --"AcceptanceContract / HumanGate / HarnessTask"--> MODELS
    GRAPH --"TechGraph / GraphNode / GraphEdge"--> MODELS
    EXECUTOR --"ExecutionResult"--> MODELS
    IO --"load / persist"--> MODELS
    EXTERNAL --"npx @cyning/harness verify"--> CLI
    %% 锚点：见 YAML 源 edges[].anchors
```

## Nodes

| ID | Label | Kind |
|----|-------|------|
| CLI | probe CLI | entry |
| MCP | MCP Server | entry |
| RUNNER | TaskRunner | service |
| BUILDER | builder.py | service |
| COMPILER | compiler.py | service |
| GRAPH | graph.py | service |
| EXECUTOR | executor.py | service |
| SAFETY | safety.py | service |
| MODELS | models.py | data |
| IO | io.py | service |
| EXTERNAL | @cyning/harness + 工作区 | external |

## Edges

| From | To | Label | Type |
|------|----|-------|------|
| CLI | RUNNER | cmd_run |  |
| CLI | GRAPH | cmd_graph_query / cmd_watch |  |
| CLI | IO | load_graph / parse_task_markdown |  |
| MCP | RUNNER | probe_run / probe_compile |  |
| MCP | IO | probe_verify |  |
| RUNNER | BUILDER | build_hat_prompt |  |
| RUNNER | COMPILER | retrieve_wiki / contract |  |
| RUNNER | GRAPH | query_subgraph |  |
| RUNNER | EXECUTOR | 真实执行 verify 命令 |  |
| EXECUTOR | SAFETY | CommandSafetyChecker.check |  |
| BUILDER | COMPILER | format_contract_table / format_wiki_context |  |
| COMPILER | MODELS | AcceptanceContract / HumanGate / HarnessTask |  |
| GRAPH | MODELS | TechGraph / GraphNode / GraphEdge |  |
| EXECUTOR | MODELS | ExecutionResult |  |
| IO | MODELS | load / persist |  |
| EXTERNAL | CLI | npx @cyning/harness verify |  |
