---
description: "\u7EDF\u4E00\u914D\u7F6E\u52A0\u8F7D\u3001\u5408\u5E76\u3001\u6821\u9A8C\
  \u4E0E\u73AF\u5883\u53D8\u91CF/CLI\u8986\u76D6"
generated_from: 95_config.graph.yaml
generator: docs/_tech_graph/scripts/graph_yaml_compile.py
graph_id: 95_config
title: "\u914D\u7F6E\u4E2D\u5FC3"
version: '2026-07-01'
---

# 配置中心

> 统一配置加载、合并、校验与环境变量/CLI覆盖

> **源文件**：`95_config.graph.yaml` · 由 `docs/_tech_graph/scripts/graph_yaml_compile.py` 生成 · 请勿直接手写本文件

```mermaid
flowchart TD
    CONFIG_MANAGER[["harness_sdk/config.py"]]
    CONFIG_FILES[["config/*.yaml"]]
    ENV_VARS[["HARNESS_* environment"]]
    CLI_OVERRIDES[["--executor-plugin / --safety-mode / --config-dir"]]
    CLI_CONFIG[["config validate / config show"]]
    EXECUTOR[["executor.py / executor_plugins"]]
    SAFETY[["safety.py"]]
    AUDIT[["audit/logger.py"]]
    CONFIG_FILES --"load directory"--> CONFIG_MANAGER
    ENV_VARS --"override"--> CONFIG_MANAGER
    CLI_OVERRIDES --"set() highest priority"--> CONFIG_MANAGER
    CONFIG_MANAGER --"read default_plugin / plugins / sandbox"--> EXECUTOR
    CONFIG_MANAGER --"read mode / config_path"--> SAFETY
    CONFIG_MANAGER --"read log_dir / retention"--> AUDIT
    CLI_CONFIG --"validate / show"--> CONFIG_MANAGER
    %% 锚点：见 YAML 源 edges[].anchors
```

## Nodes

| ID | Label | Kind |
|----|-------|------|
| CONFIG_MANAGER | harness_sdk/config.py | service |
| CONFIG_FILES | config/*.yaml | storage |
| ENV_VARS | HARNESS_* environment | input |
| CLI_OVERRIDES | --executor-plugin / --safety-mode / --config-dir | input |
| CLI_CONFIG | config validate / config show | entry |
| EXECUTOR | executor.py / executor_plugins | service |
| SAFETY | safety.py | service |
| AUDIT | audit/logger.py | service |

## Edges

| From | To | Label | Type |
|------|----|-------|------|
| CONFIG_FILES | CONFIG_MANAGER | load directory |  |
| ENV_VARS | CONFIG_MANAGER | override |  |
| CLI_OVERRIDES | CONFIG_MANAGER | set() highest priority |  |
| CONFIG_MANAGER | EXECUTOR | read default_plugin / plugins / sandbox |  |
| CONFIG_MANAGER | SAFETY | read mode / config_path |  |
| CONFIG_MANAGER | AUDIT | read log_dir / retention |  |
| CLI_CONFIG | CONFIG_MANAGER | validate / show |  |
