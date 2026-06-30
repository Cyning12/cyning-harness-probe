---
description: "\u57FA\u4E8E FastMCP \u66B4\u9732 probe_compile / probe_run / probe_audit\
  \ / probe_verify"
generated_from: 85_mcp.graph.yaml
generator: docs/_tech_graph/scripts/graph_yaml_compile.py
graph_id: 85_mcp
title: "MCP Server \u4E0E Tools"
version: '2026-06-30'
---

# MCP Server 与 Tools

> 基于 FastMCP 暴露 probe_compile / probe_run / probe_audit / probe_verify

> **源文件**：`85_mcp.graph.yaml` · 由 `docs/_tech_graph/scripts/graph_yaml_compile.py` 生成 · 请勿直接手写本文件

```mermaid
flowchart TD
    MCP[["MCP Server"]]
    TOOLS[["tools.py"]]
    RUNNER[["TaskRunner"]]
    IO[["io.py"]]
    MCP_HOST[["MCP Host"]]
    MCP --"register tools"--> TOOLS
    TOOLS --"probe_run / probe_compile"--> RUNNER
    TOOLS --"probe_verify / probe_audit"--> IO
    MCP_HOST --"stdio / sse transport"--> MCP
    %% 锚点：见 YAML 源 edges[].anchors
```

## Nodes

| ID | Label | Kind |
|----|-------|------|
| MCP | MCP Server | entry |
| TOOLS | tools.py | service |
| RUNNER | TaskRunner | service |
| IO | io.py | service |
| MCP_HOST | MCP Host | external |

## Edges

| From | To | Label | Type |
|------|----|-------|------|
| MCP | TOOLS | register tools |  |
| TOOLS | RUNNER | probe_run / probe_compile |  |
| TOOLS | IO | probe_verify / probe_audit |  |
| MCP_HOST | MCP | stdio / sse transport |  |
