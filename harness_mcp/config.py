"""MCP Server configuration helpers."""

from __future__ import annotations

from pathlib import Path

import yaml


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_mcp_config(path: str | Path) -> dict:
    cfg_path = Path(path)
    if not cfg_path.exists():
        return {}
    return yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}


def get_default_graph_path(config: dict) -> Path:
    raw = config.get("probe", {}).get("default_graph", "data/graph/sample_graph_v2.json")
    path = Path(raw)
    if not path.is_absolute():
        path = _repo_root() / path
    return path


def get_default_wiki_path(config: dict) -> Path:
    raw = config.get("probe", {}).get("default_wiki", "data/wiki/syntheses_stub.json")
    path = Path(raw)
    if not path.is_absolute():
        path = _repo_root() / path
    return path
