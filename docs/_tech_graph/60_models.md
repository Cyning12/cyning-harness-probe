---
description: "\u6838\u5FC3\u6570\u636E\u7ED3\u6784\u5B9A\u4E49\uFF1Atask\u3001contract\u3001\
  graph\u3001run\u3001prompt\u3001execution"
generated_from: 60_models.graph.yaml
generator: docs/_tech_graph/scripts/graph_yaml_compile.py
graph_id: 60_models
title: "Pydantic \u6570\u636E\u6A21\u578B"
version: '2026-06-30'
---

# Pydantic 数据模型

> 核心数据结构定义：task、contract、graph、run、prompt、execution

> **源文件**：`60_models.graph.yaml` · 由 `docs/_tech_graph/scripts/graph_yaml_compile.py` 生成 · 请勿直接手写本文件

```mermaid
flowchart TD
    HarnessTask[["HarnessTask"]]
    AcceptanceContract[["AcceptanceContract"]]
    HumanGate[["HumanGate"]]
    TechGraph[["TechGraph"]]
    TaskRunGraph[["TaskRunGraph"]]
    ExecutionResult[["ExecutionResult"]]
    HarnessTask --"contracts[]"--> AcceptanceContract
    HarnessTask --"human_gates[]"--> HumanGate
    TechGraph --"freeze_id 校验"--> HarnessTask
    TaskRunGraph --"task_path / l0_freeze_id"--> HarnessTask
    ExecutionResult --"evidence"--> TaskRunGraph
    %% 锚点：见 YAML 源 edges[].anchors
```

## Nodes

| ID | Label | Kind |
|----|-------|------|
| HarnessTask | HarnessTask | data |
| AcceptanceContract | AcceptanceContract | data |
| HumanGate | HumanGate | data |
| TechGraph | TechGraph | data |
| TaskRunGraph | TaskRunGraph | data |
| ExecutionResult | ExecutionResult | data |

## Edges

| From | To | Label | Type |
|------|----|-------|------|
| HarnessTask | AcceptanceContract | contracts[] |  |
| HarnessTask | HumanGate | human_gates[] |  |
| TechGraph | HarnessTask | freeze_id 校验 |  |
| TaskRunGraph | HarnessTask | task_path / l0_freeze_id |  |
| ExecutionResult | TaskRunGraph | evidence |  |
