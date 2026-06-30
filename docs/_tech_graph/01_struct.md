---
description: "harness-probe \u4E2D Pydantic \u4E0E dataclass \u5B9A\u4E49\u7684\u6838\
  \u5FC3\u6A21\u578B"
generated_from: 01_struct.graph.yaml
generator: docs/_tech_graph/scripts/graph_yaml_compile.py
graph_id: 01_struct
title: "\u6838\u5FC3\u6570\u636E\u7ED3\u6784"
version: '2026-06-30'
---

# 核心数据结构

> harness-probe 中 Pydantic 与 dataclass 定义的核心模型

> **源文件**：`01_struct.graph.yaml` · 由 `docs/_tech_graph/scripts/graph_yaml_compile.py` 生成 · 请勿直接手写本文件

```mermaid
flowchart TD
    HarnessTask[["HarnessTask"]]
    AcceptanceContract[["AcceptanceContract"]]
    HumanGate[["HumanGate"]]
    TechGraph[["TechGraph"]]
    GraphNode[["GraphNode"]]
    GraphEdge[["GraphEdge"]]
    TaskRunGraph[["TaskRunGraph"]]
    TaskRunNode[["TaskRunNode"]]
    CompiledPrompt[["CompiledPrompt"]]
    ExecutionResult[["ExecutionResult"]]
    SafetyConfig[["SafetyConfig"]]
    HarnessTask --"contracts[]"--> AcceptanceContract
    HarnessTask --"human_gates[]"--> HumanGate
    TechGraph --"nodes[]"--> GraphNode
    TechGraph --"edges[]"--> GraphEdge
    TaskRunGraph --"nodes[]"--> TaskRunNode
    TaskRunNode --"contract_refs[]"--> AcceptanceContract
    CompiledPrompt --"static + semi_static + dynamic"--> HarnessTask
    ExecutionResult --"blocked / dry_run / reason"--> SafetyConfig
    %% 锚点：见 YAML 源 edges[].anchors
```

## Nodes

| ID | Label | Kind |
|----|-------|------|
| HarnessTask | HarnessTask | data |
| AcceptanceContract | AcceptanceContract | data |
| HumanGate | HumanGate | data |
| TechGraph | TechGraph | data |
| GraphNode | GraphNode | data |
| GraphEdge | GraphEdge | data |
| TaskRunGraph | TaskRunGraph | data |
| TaskRunNode | TaskRunNode | data |
| CompiledPrompt | CompiledPrompt | data |
| ExecutionResult | ExecutionResult | data |
| SafetyConfig | SafetyConfig | data |

## Edges

| From | To | Label | Type |
|------|----|-------|------|
| HarnessTask | AcceptanceContract | contracts[] |  |
| HarnessTask | HumanGate | human_gates[] |  |
| TechGraph | GraphNode | nodes[] |  |
| TechGraph | GraphEdge | edges[] |  |
| TaskRunGraph | TaskRunNode | nodes[] |  |
| TaskRunNode | AcceptanceContract | contract_refs[] |  |
| CompiledPrompt | HarnessTask | static + semi_static + dynamic |  |
| ExecutionResult | SafetyConfig | blocked / dry_run / reason |  |
