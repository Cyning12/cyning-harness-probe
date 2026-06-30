"""MCP Resources · harness-probe"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from harness_mcp.config import get_default_graph_path, load_mcp_config
from harness_probe.io import load_graph, parse_task_markdown


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


async def get_current_freeze_id(
    task_path: str,
    config_path: str | None = None,
) -> str:
    """Resource: harness://freeze_id/current

    返回当前 task + graph 的 freeze_id 一致性状态。
    """
    default_config = _repo_root() / "config" / "probe_config.yaml"
    config = load_mcp_config(config_path or default_config)

    graph_path = get_default_graph_path(config)
    task_path_obj = Path(task_path)
    if not task_path_obj.is_absolute():
        task_path_obj = _repo_root() / task_path_obj

    graph = load_graph(graph_path)
    task = parse_task_markdown(task_path_obj)

    graph_freeze = graph.freeze_id
    task_freeze = task.freeze_id or "（未设置）"
    consistent = graph_freeze == task_freeze

    return json.dumps(
        {
            "task_freeze_id": task_freeze,
            "graph_freeze_id": graph_freeze,
            "consistent": consistent,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        },
        ensure_ascii=False,
    )
