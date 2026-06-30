---
description: "\u6309\u5E3D\u5B50\u7C7B\u578B\u7EC4\u88C5 static_prefix / semi_static\
  \ / dynamic_suffix"
generated_from: 40_builder.graph.yaml
generator: docs/_tech_graph/scripts/graph_yaml_compile.py
graph_id: 40_builder
title: "Prompt \u4E09\u6BB5\u5F0F\u7EC4\u88C5"
version: '2026-06-30'
---

# Prompt 三段式组装

> 按帽子类型组装 static_prefix / semi_static / dynamic_suffix

> **源文件**：`40_builder.graph.yaml` · 由 `docs/_tech_graph/scripts/graph_yaml_compile.py` 生成 · 请勿直接手写本文件

```mermaid
flowchart TD
    BUILDER[["builder.py"]]
    COMPILER[["compiler.py"]]
    MODELS[["CompiledPrompt"]]
    BUILDER --"format_contract_table / format_wiki_context"--> COMPILER
    BUILDER --"CompiledPrompt"--> MODELS
    %% 锚点：见 YAML 源 edges[].anchors
```

## Nodes

| ID | Label | Kind |
|----|-------|------|
| BUILDER | builder.py | service |
| COMPILER | compiler.py | service |
| MODELS | CompiledPrompt | data |

## Edges

| From | To | Label | Type |
|------|----|-------|------|
| BUILDER | COMPILER | format_contract_table / format_wiki_context |  |
| BUILDER | MODELS | CompiledPrompt |  |
