"""Harness SDK · 无副作用的 Harness 编译核心。

输入：graph_v2、task.md、wiki 摘要
输出：Subagent Prompt、AcceptanceContract、TaskRunGraph

本层禁止：读文件、写文件、print、访问环境变量。
"""

from __future__ import annotations

from harness_sdk.builder import build_hat_prompt, build_subagent_prompt
from harness_sdk.compiler import (
    compile_contracts_from_task,
    format_contract_table,
    format_wiki_context,
    parse_human_gates,
    retrieve_wiki,
    validate_human_gate_rules,
)
from harness_sdk.config import ConfigError, ConfigManager
from harness_sdk.exceptions import BlockedError
from harness_sdk.executor import SubprocessExecutor, VerifyExecutor
from harness_sdk.graph import query_subgraph, subgraph_to_mermaid
from harness_sdk.models import (
    AcceptanceContract,
    CompiledPrompt,
    ExecutionResult,
    GraphAnchor,
    GraphEdge,
    GraphNode,
    HarnessTask,
    HumanGate,
    RunNodeStatus,
    SubgraphResult,
    TaskRunGraph,
    TaskRunNode,
    TechGraph,
    WikiEntry,
)
from harness_sdk.runner import TaskRunner

__all__ = [
    # builder
    "build_hat_prompt",
    "build_subagent_prompt",
    # compiler
    "compile_contracts_from_task",
    "format_contract_table",
    "format_wiki_context",
    "parse_human_gates",
    "retrieve_wiki",
    "validate_human_gate_rules",
    # config
    "ConfigError",
    "ConfigManager",
    # exceptions
    "BlockedError",
    # executor
    "SubprocessExecutor",
    "VerifyExecutor",
    # graph
    "query_subgraph",
    "subgraph_to_mermaid",
    # models
    "AcceptanceContract",
    "CompiledPrompt",
    "ExecutionResult",
    "GraphAnchor",
    "GraphEdge",
    "GraphNode",
    "HarnessTask",
    "HumanGate",
    "RunNodeStatus",
    "SubgraphResult",
    "TaskRunGraph",
    "TaskRunNode",
    "TechGraph",
    "WikiEntry",
    # runner
    "TaskRunner",
]
