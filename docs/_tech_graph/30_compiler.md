---
description: "\u89E3\u6790 task.md\u3001\u7F16\u8BD1 AcceptanceContract\u3001\u6821\
  \u9A8C human_gate\u3001\u68C0\u7D22 Wiki"
generated_from: 30_compiler.graph.yaml
generator: docs/_tech_graph/scripts/graph_yaml_compile.py
graph_id: 30_compiler
title: task parser + contract compiler
version: '2026-06-30'
---

# task parser + contract compiler

> 解析 task.md、编译 AcceptanceContract、校验 human_gate、检索 Wiki

> **源文件**：`30_compiler.graph.yaml` · 由 `docs/_tech_graph/scripts/graph_yaml_compile.py` 生成 · 请勿直接手写本文件

```mermaid
flowchart TD
    COMPILER[["compiler.py"]]
    MODELS[["models.py"]]
    COMPILER --"AcceptanceContract / HumanGate / HarnessTask / WikiEntry"--> MODELS
    %% 锚点：见 YAML 源 edges[].anchors
```

## Nodes

| ID | Label | Kind |
|----|-------|------|
| COMPILER | compiler.py | service |
| MODELS | models.py | data |

## Edges

| From | To | Label | Type |
|------|----|-------|------|
| COMPILER | MODELS | AcceptanceContract / HumanGate / HarnessTask / WikiEntry |  |
