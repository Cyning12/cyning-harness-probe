---
description: "SubprocessExecutor + CommandSafetyChecker + \u6267\u884C\u65E5\u5FD7"
generated_from: 90_executor.graph.yaml
generator: docs/_tech_graph/scripts/graph_yaml_compile.py
graph_id: 90_executor
title: "\u771F\u5B9E\u6267\u884C\u5668\u4E0E\u5B89\u5168\u6821\u9A8C"
version: '2026-06-30'
---

# 真实执行器与安全校验

> SubprocessExecutor + CommandSafetyChecker + 执行日志

> **源文件**：`90_executor.graph.yaml` · 由 `docs/_tech_graph/scripts/graph_yaml_compile.py` 生成 · 请勿直接手写本文件

```mermaid
flowchart TD
    EXECUTOR[["SubprocessExecutor"]]
    SAFETY[["CommandSafetyChecker"]]
    SAFETY_CONFIG[["SafetyConfig / SafetyMode"]]
    EXECUTION_LOG[["execution_log_*.jsonl"]]
    MODELS[["ExecutionResult"]]
    EXECUTOR --"check(cmd)"--> SAFETY
    SAFETY --"配置模式/白名单/黑名单"--> SAFETY_CONFIG
    EXECUTOR --"append JSONL"--> EXECUTION_LOG
    EXECUTOR --"return ExecutionResult"--> MODELS
    %% 锚点：见 YAML 源 edges[].anchors
```

## Nodes

| ID | Label | Kind |
|----|-------|------|
| EXECUTOR | SubprocessExecutor | service |
| SAFETY | CommandSafetyChecker | service |
| SAFETY_CONFIG | SafetyConfig / SafetyMode | data |
| EXECUTION_LOG | execution_log_*.jsonl | storage |
| MODELS | ExecutionResult | data |

## Edges

| From | To | Label | Type |
|------|----|-------|------|
| EXECUTOR | SAFETY | check(cmd) |  |
| SAFETY | SAFETY_CONFIG | 配置模式/白名单/黑名单 |  |
| EXECUTOR | EXECUTION_LOG | append JSONL |  |
| EXECUTOR | MODELS | return ExecutionResult |  |
