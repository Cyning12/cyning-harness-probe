"""Harness Probe · MCP Server"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from mcp.server import FastMCP

from harness_mcp.config import load_mcp_config
from harness_mcp.resources import get_current_freeze_id
from harness_mcp.tools import probe_audit, probe_compile, probe_run, probe_verify


def _default_task_path(config: dict) -> str:
    raw = config.get("mcp", {}).get("default_task", "data/tasks/sample_task.md")
    path = Path(raw)
    if not path.is_absolute():
        path = Path(__file__).resolve().parent.parent / path
    return str(path)


def create_server(config_path: str | None = None) -> FastMCP:
    if config_path is None:
        config_path = os.environ.get("HPROBE_CONFIG", "config/probe_config.yaml")
    config = load_mcp_config(config_path)
    default_task = _default_task_path(config)

    mcp = FastMCP("harness-probe")

    @mcp.tool(name="probe_compile")
    async def probe_compile_tool(
        task_path: str,
        entry_node: str,
        hat: str,
        graph_path: str | None = None,
        wiki_path: str | None = None,
    ) -> str:
        return await probe_compile(
            task_path=task_path,
            entry_node=entry_node,
            hat=hat,
            graph_path=graph_path,
            wiki_path=wiki_path,
            config_path=config_path,
        )

    @mcp.tool(name="probe_run")
    async def probe_run_tool(
        task_path: str,
        entry_node: str,
        from_hat: str,
        to_hat: str,
        graph_path: str | None = None,
        wiki_path: str | None = None,
        mock: bool = True,
    ) -> str:
        return await probe_run(
            task_path=task_path,
            entry_node=entry_node,
            from_hat=from_hat,
            to_hat=to_hat,
            graph_path=graph_path,
            wiki_path=wiki_path,
            mock=mock,
            config_path=config_path,
        )

    @mcp.tool(name="probe_audit")
    async def probe_audit_tool(
        run_output_path: str,
        mode: str = "independent",
    ) -> str:
        return await probe_audit(run_output_path=run_output_path, mode=mode)

    @mcp.tool(name="probe_verify")
    async def probe_verify_tool(task_path: str) -> str:
        return await probe_verify(task_path=task_path)

    @mcp.resource("harness://freeze_id/current")
    async def freeze_id_resource() -> str:
        return await get_current_freeze_id(
            task_path=default_task,
            config_path=config_path,
        )

    return mcp


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Harness Probe MCP Server")
    parser.add_argument(
        "--config",
        default=None,
        help="probe config yaml path (default: HPROBE_CONFIG env or config/probe_config.yaml)",
    )
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "sse"],
        help="MCP transport (default: stdio)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="SSE port (default: 8080)",
    )
    args = parser.parse_args(argv)

    mcp = create_server(config_path=args.config)

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="sse", port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
