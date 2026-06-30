---
description: "\u89E3\u6790 Markdown task\u3001\u63D0\u53D6 AcceptanceContract \u4E0E\
  \ human_gate"
generated_from: 30_compiler.graph.yaml
generator: docs/_tech_graph/scripts/graph_yaml_compile.py
graph_id: 30_compiler
title: "task parser + contract \u7F16\u8BD1"
version: '2026-06-30'
---

# task parser + contract 编译

> 解析 Markdown task、提取 AcceptanceContract 与 human_gate

> **源文件**：`30_compiler.graph.yaml` · 由 `docs/_tech_graph/scripts/graph_yaml_compile.py` 生成 · 请勿直接手写本文件

```mermaid
flowchart TD
    COMPILER[["compiler.py"]]
    IO[["io.py"]]
    MODELS[["models.py"]]
    COMPILER --"parse_task_markdown"--> IO
    COMPILER --"AcceptanceContract / HumanGate / HarnessTask"--> MODELS
    %% 锚点：见 YAML 源 edges[].anchors
```

## Nodes

| ID | Label | Kind |
|----|-------|------|
| COMPILER | compiler.py | service |
| IO | io.py | service |
| MODELS | models.py | data |

## Edges

| From | To | Label | Type |
|------|----|-------|------|
| COMPILER | IO | parse_task_markdown |  |
| COMPILER | MODELS | AcceptanceContract / HumanGate / HarnessTask |  |
