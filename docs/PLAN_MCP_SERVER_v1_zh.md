# MCP Server 技术方案 · harness-probe Tool / Resource 设计（v1）

| 项 | 内容 |
| --- | --- |
| **状态** | `planning` |
| **版本** | v1 |
| **日期** | 2026-06-29 |
| **目标** | 将 Probe 核心能力封装为 MCP Server，供 Cursor / Claude Desktop / Kimi 等 Host 调用 |

---

## 1. 技术选型

- **MCP SDK**：`mcp>=1.0.0`（官方 Python SDK）或 `fastmcp`（若需更简洁装饰器）
- **Server 入口**：`python -m harness_probe.mcp` 或 `harness-probe mcp`
- **传输**：默认 `stdio`（本地 Agent 直连）；可选 `sse`（网络模式）
- **依赖**：复用 `harness_sdk` 核心库，不直接读文件（IO 由 MCP Server 调用方传入路径）

---

## 2. Tool 清单

### 2.1 `probe_compile`

**功能**：编译指定帽子的 Subagent Prompt，返回 static / semi_static / dynamic 三段内容。

**输入参数**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `task_path` | string | ✅ | task.md 绝对路径 |
| `entry_node` | string | ✅ | L0 图谱入口节点 |
| `hat` | string | ✅ | 帽子，如 "30"、"40"、"10-spec"、"20-review"、"50-reinspect" |
| `graph_path` | string | ❌ | graph.json 绝对路径；默认取 config 中 `default_graph` |
| `wiki_path` | string | ❌ | wiki JSON 绝对路径；默认取 config 中 `default_wiki` |
| `dynamic_query` | string | ❌ | 覆盖 task 中的动态查询 |

**输出格式**

```json
{
  "session_id": "abc123",
  "freeze_id": "HARNESS-PROBE-SAMPLE-V0.2",
  "hat": "30",
  "static_prefix": "# [HARNESS PROBE] System...",
  "semi_static": "## L1 · AcceptanceContract...",
  "dynamic_suffix": "## 动态任务指令...",
  "static_char_count": 1337,
  "dynamic_char_count": 383,
  "static_ratio": 0.78,
  "prompt_path": "/abs/path/to/outputs/prompt_abc123_hat30.md"
}
```

**错误码**

- `BLOCKED_HUMAN_GATE`：human_gate pending 阻塞当前 hat
- `MISSING_FREEZE_ID`：task 或 graph 中 freeze_id 缺失
- `CONTRACT_OVERFLOW`：AcceptanceContract 超过 15 行

---

### 2.2 `probe_run`

**功能**：串行模拟执行多顶帽子，生成 L1.5 task_run 轨迹。

**输入参数**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `task_path` | string | ✅ | task.md 绝对路径 |
| `entry_node` | string | ✅ | 入口节点 |
| `from_hat` | string | ✅ | 起始帽子 |
| `to_hat` | string | ✅ | 结束帽子 |
| `graph_path` | string | ❌ | graph.json 路径 |
| `wiki_path` | string | ❌ | wiki JSON 路径 |
| `mock` | boolean | ❌ | 是否使用 Mock LLM，默认 true |
| `resume_from` | string | ❌ | 已有 task_run JSON 路径，从失败点恢复 |

**输出格式**

```json
{
  "session_id": "abc123",
  "status": "done",
  "run_output_path": "/abs/path/to/outputs/task_run_abc123.json",
  "nodes": [
    {
      "hat": "30",
      "status": "done",
      "contract_refs": ["F1", "F2", "F3"],
      "evidence": "{\"F1\": \"pass\", ...}"
    },
    {
      "hat": "40",
      "status": "done",
      "contract_refs": ["F1", "F2", "F3"],
      "evidence": "{...}"
    }
  ]
}
```

---

### 2.3 `probe_audit`

**功能**：读取 task_run.json，生成验收表 + 合并建议 / 打回建议。

**输入参数**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `run_output_path` | string | ✅ | task_run JSON 绝对路径 |
| `mode` | string | ❌ | "independent" 或 "global"，默认 "independent" |

**输出格式**

```json
{
  "verdict": "pass",
  "summary": "F1/F2/F3 全部通过，证据完整",
  "contract_table": [
    {"ref": "F1", "pass_fail": "pass", "evidence": "pytest tests/test_rag_fallback.py"},
    {"ref": "F2", "pass_fail": "pass", "evidence": "pytest tests/test_rpc_retry.py"},
    {"ref": "F3", "pass_fail": "pass", "evidence": "python -m src.probe verify"}
  ],
  "recommendation": "CLOSE · 可合并"
}
```

若 verdict 为 `fail`：

```json
{
  "verdict": "fail",
  "summary": "F2 证据不足",
  "contract_table": [...],
  "recommendation": "打回至 30 · 补跑 verify_cmd 并附输出摘要",
  "next_hat": "30"
}
```

---

### 2.4 `probe_verify`

**功能**：PRE_SPAWN_VERIFY，校验 task 人闸与 Harness 规则，不生成 Prompt。

**输入参数**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `task_path` | string | ✅ | task.md 绝对路径 |

**输出格式**

```json
{
  "ok": true,
  "errors": [],
  "blocked_hats": []
}
```

若失败：

```json
{
  "ok": false,
  "errors": ["HUMAN-GATE-AUDIT-R1-MISSING: blocks_hats 含 30 时须含 HG-AUDIT-R1"],
  "blocked_hats": ["30"]
}
```

---

### 2.5 Tool 参数 JSON Schema 示例

```python
@mcp_server.tool()
async def probe_compile(
    task_path: str,
    entry_node: str,
    hat: str,
    graph_path: str | None = None,
    wiki_path: str | None = None,
    dynamic_query: str = "",
) -> str:
    """编译指定帽子的 Subagent Prompt。"""
    ...
```

---

## 3. Resource 清单

### 3.1 `harness://freeze_id/current`

**功能**：返回当前 task + graph 的 freeze_id，供 Agent 在每次调用前感知版本。

**输出格式**

```json
{
  "task_freeze_id": "HARNESS-PROBE-SAMPLE-V0.2",
  "graph_freeze_id": "HARNESS-PROBE-SAMPLE-V0.2",
  "consistent": true,
  "checked_at": "2026-06-29T10:00:00Z"
}
```

**变更感知机制**：

- Agent 在调用 `probe_compile` 前，先 `read_resource("harness://freeze_id/current")`。
- MCP Server 每次 read 时实时读取 graph.json 和 task.md，返回当前 freeze_id。
- 若 `consistent: false`，Agent 应暂停并请求人类确认是否重新编译。

### 3.2 `harness://task/{task_path}/run/latest`

**功能**：返回某 task 最近一次 `probe_run` 的结果摘要。

**输出格式**

```json
{
  "task_path": "/abs/path/to/data/tasks/sample_task.md",
  "latest_session_id": "abc123",
  "latest_status": "done",
  "summary": "30/40 全部通过"
}
```

### 3.3 Resource 订阅（可选）

```python
@mcp_server.resource("harness://freeze_id/current")
async def get_current_freeze_id() -> str:
    result = check_freeze_idConsistency(config)
    return json.dumps(result, ensure_ascii=False)
```

由于 MCP stdio 不支持服务端主动推送，freeze_id 变更感知采用**客户端轮询**模式：

```python
# Agent 侧示例
async def ensure_fresh(task_path: str, graph_path: str, last_seen: dict) -> bool:
    current = await mcp_client.read_resource("harness://freeze_id/current")
    data = json.loads(current)
    if not data["consistent"]:
        return False
    if data["graph_freeze_id"] != last_seen.get("graph_freeze_id"):
        return False
    return True
```

---

## 4. Server 实现骨架

```python
# harness_probe/mcp_server.py
from __future__ import annotations

import json
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

from harness_sdk import (
    build_hat_prompt,
    gate_scan,
    pre_spawn_verify,
    query_subgraph,
    retrieve_wiki,
)
from harness_probe.io import load_graph, load_wiki_stub, parse_task_markdown


class ProbeMcpServer:
    def __init__(self, config: dict):
        self.config = config
        self.server = Server("harness-probe")
        self._register_tools()
        self._register_resources()

    def _register_tools(self) -> None:
        @self.server.tool()
        async def probe_compile(
            task_path: str,
            entry_node: str,
            hat: str,
            graph_path: str | None = None,
            wiki_path: str | None = None,
            dynamic_query: str = "",
        ) -> str:
            graph = load_graph(Path(graph_path or self.config["default_graph"]))
            task = parse_task_markdown(Path(task_path), dynamic_query)
            gate_scan(task, [hat])
            pre_spawn_verify(task)
            subgraph = query_subgraph(graph, entry_node, depth=2)
            wiki_entries = retrieve_wiki(
                load_wiki_stub(wiki_path or self.config["default_wiki"]),
                task.dynamic_query,
                entry_node,
            )
            compiled = build_hat_prompt(hat, task, graph, subgraph, wiki_entries)
            # persist + return
            return json.dumps({
                "session_id": "...",
                "freeze_id": graph.freeze_id,
                "hat": hat,
                "static_prefix": compiled.static_prefix,
                "semi_static": compiled.semi_static,
                "dynamic_suffix": compiled.dynamic_suffix,
            }, ensure_ascii=False)

        @self.server.tool()
        async def probe_verify(task_path: str) -> str:
            from harness_sdk.compiler import validate_task_markdown
            errors = validate_task_markdown(Path(task_path))
            return json.dumps({
                "ok": not errors,
                "errors": errors,
            }, ensure_ascii=False)

    def _register_resources(self) -> None:
        @self.server.resource("harness://freeze_id/current")
        async def freeze_id_resource() -> str:
            # 实时读取
            ...

    async def run(self) -> None:
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )


def main() -> None:
    import asyncio
    import yaml
    cfg_path = Path("config/probe_config.yaml")
    config = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    server = ProbeMcpServer(config.get("probe", {}))
    asyncio.run(server.run())
```

---

## 5. CLI 启动方式

```bash
# stdio 模式（默认，供 Claude Desktop / Cursor 使用）
python -m harness_probe.mcp_server

# 或全局命令
harness-probe mcp

# sse 模式（网络调试）
harness-probe mcp --transport sse --port 8080
```

---

## 6. 客户端配置示例（Claude Desktop）

```json
{
  "mcpServers": {
    "harness-probe": {
      "command": "harness-probe",
      "args": ["mcp"],
      "env": {
        "HPROBE_CONFIG": "/abs/path/to/config/probe_config.yaml"
      }
    }
  }
}
```

---

## 7. 安全与边界

| 项 | 约束 |
| --- | --- |
| 文件访问 | MCP Server 只读指定 `task_path`、`graph_path`、`wiki_path`；不写业务代码 |
| 网络 | 默认 stdio，无网络暴露 |
| LLM 调用 | `probe_run` 的 `mock=false` 模式需要显式授权，默认关闭 |
| freeze_id 一致性 | 由 Resource 轮询保证；Server 不主动推送 |

---

## 8. 与长程规划的对应关系

| 长程规划阶段 | 本方案覆盖 |
| --- | --- |
| Phase 2.3 · AcceptanceContract 编译器增强 | `probe_compile` 可暴露 contract 编译结果 |
| Phase 3.1 · MCP Server 基础框架 | 本方案主体 |
| Phase 3.2 · MCP 资源变更通知 | `harness://freeze_id/current` + 客户端轮询 |
| Phase 4.3 · 一等 Agent 审计助手 | `probe_audit` 工具 |

---

## 给 Cursor

`MCP Server`、`probe_compile`、`probe_run`、`probe_audit`、`probe_verify`、`harness://freeze_id/current`、stdio、sse、Resource 轮询
