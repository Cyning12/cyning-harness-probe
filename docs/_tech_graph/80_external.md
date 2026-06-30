---
description: "@cyning/harness \u4EA7\u54C1\u5305\u4E0E Ink \u5DE5\u4F5C\u533A\u89C4\
  \u8303"
generated_from: 80_external.graph.yaml
generator: docs/_tech_graph/scripts/graph_yaml_compile.py
graph_id: 80_external
title: "\u5916\u90E8\u4F9D\u8D56"
version: '2026-06-30'
---

# 外部依赖

> @cyning/harness 产品包与 Ink 工作区规范

> **源文件**：`80_external.graph.yaml` · 由 `docs/_tech_graph/scripts/graph_yaml_compile.py` 生成 · 请勿直接手写本文件

```mermaid
flowchart TD
    CYNING_HARNESS[["@cyning/harness"]]
    WORKSPACE[["Ink 工作区"]]
    CLI --"shell out npx verify"--> CYNING_HARNESS
    RUNNER --"pre_spawn_verify / gate_scan 对齐 PROMPT v1.1"--> WORKSPACE
    %% 锚点：见 YAML 源 edges[].anchors
```

## Nodes

| ID | Label | Kind |
|----|-------|------|
| CYNING_HARNESS | @cyning/harness | external |
| WORKSPACE | Ink 工作区 | external |

## Edges

| From | To | Label | Type |
|------|----|-------|------|
| CLI | CYNING_HARNESS | shell out npx verify | optional_depends_on |
| RUNNER | WORKSPACE | pre_spawn_verify / gate_scan 对齐 PROMPT v1.1 | references |
