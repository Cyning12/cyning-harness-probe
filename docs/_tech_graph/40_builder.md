---
description: "\u6309\u5E3D\u5B50\u751F\u6210 static / semi_static / dynamic \u4E09\
  \u6BB5\u5F0F Prompt"
generated_from: 40_builder.graph.yaml
generator: docs/_tech_graph/scripts/graph_yaml_compile.py
graph_id: 40_builder
title: "Prompt \u4E09\u6BB5\u5F0F\u7EC4\u88C5"
version: '2026-06-30'
---

# Prompt 三段式组装

> 按帽子生成 static / semi_static / dynamic 三段式 Prompt

> **源文件**：`40_builder.graph.yaml` · 由 `docs/_tech_graph/scripts/graph_yaml_compile.py` 生成 · 请勿直接手写本文件

```mermaid
flowchart TD
    BUILDER[["builder.py"]]
    COMPILER[["compiler.py"]]
    BUILDER --"format_contract_table / format_wiki_context"--> COMPILER
    %% 锚点：见 YAML 源 edges[].anchors
```

## Nodes

| ID | Label | Kind |
|----|-------|------|
| BUILDER | builder.py | service |
| COMPILER | compiler.py | service |

## Edges

| From | To | Label | Type |
|------|----|-------|------|
| BUILDER | COMPILER | format_contract_table / format_wiki_context |  |
