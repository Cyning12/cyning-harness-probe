"""MCP resource tests"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness_mcp.server import create_server


REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def mcp():
    return create_server()


@pytest.mark.asyncio
async def test_mcp_resource_freeze_id(mcp):
    result = await mcp.read_resource("harness://freeze_id/current")
    text = result[0].content
    data = json.loads(text)
    assert "graph_freeze_id" in data
    assert "task_freeze_id" in data
    assert "consistent" in data
    assert "checked_at" in data
