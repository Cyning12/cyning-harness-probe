---
description: "@cyning/harness \u4EA7\u54C1\u5305\u3001Ink \u5DE5\u4F5C\u533A\u3001\
  MCP Host"
generated_from: 80_external.graph.yaml
generator: docs/_tech_graph/scripts/graph_yaml_compile.py
graph_id: 80_external
title: "\u5916\u90E8\u4F9D\u8D56"
version: '2026-06-30'
---

# 外部依赖

> @cyning/harness 产品包、Ink 工作区、MCP Host

> **源文件**：`80_external.graph.yaml` · 由 `docs/_tech_graph/scripts/graph_yaml_compile.py` 生成 · 请勿直接手写本文件

```mermaid
flowchart TD
    HARNESS_PKG[["@cyning/harness"]]
    INK_WORKSPACE[["Ink 工作区"]]
    MCP_HOST[["MCP Host"]]
    CLI[["probe CLI"]]
    MCP[["MCP Server"]]
    HARNESS_PKG --"npx @cyning/harness verify"--> CLI
    INK_WORKSPACE --"共享 graph.json / task 规范"--> CLI
    MCP_HOST --"stdio / sse transport"--> MCP
    %% 锚点：见 YAML 源 edges[].anchors
```

## Nodes

| ID | Label | Kind |
|----|-------|------|
| HARNESS_PKG | @cyning/harness | external |
| INK_WORKSPACE | Ink 工作区 | external |
| MCP_HOST | MCP Host | external |
| CLI | probe CLI | entry |
| MCP | MCP Server | entry |

## Edges

| From | To | Label | Type |
|------|----|-------|------|
| HARNESS_PKG | CLI | npx @cyning/harness verify |  |
| INK_WORKSPACE | CLI | 共享 graph.json / task 规范 |  |
| MCP_HOST | MCP | stdio / sse transport |  |
