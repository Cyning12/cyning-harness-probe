#!/usr/bin/env python3
"""graph_yaml_compile.py · 从 .graph.yaml 生成 .md 人类友好版"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml


GRAPH_DIR = Path(__file__).resolve().parent.parent


def shape_for_node(label: str) -> str:
    if label.startswith(">"):
        return f'["{label}"]'
    if "?" in label:
        return f'{{"{label}"}}'
    if any(k in label for k in ("数据库", "持久化", "存储")):
        return f'(("{label}"))'
    return f'[["{label}"]]'


def edge_mark(edge: dict) -> str:
    if "mark" in edge:
        return edge["mark"]
    label = edge.get("label", "")
    if label == "->":
        return ""
    return label


def escape_mermaid(label: str) -> str:
    return label.replace('"', '#quot;')


def render_mermaid(graph: dict) -> str:
    lines = ["```mermaid", "flowchart TD"]
    for node in graph.get("nodes", []):
        nid = node["id"]
        shape = shape_for_node(node.get("label", nid))
        lines.append(f"    {nid}{shape}")
    for edge in graph.get("edges", []):
        mark = edge_mark(edge)
        src = edge["from"]
        dst = edge["to"]
        if mark:
            lines.append(f'    {src} --"{escape_mermaid(mark)}"--> {dst}')
        else:
            lines.append(f"    {src} --> {dst}")
    lines.append("    %% 锚点：见 YAML 源 edges[].anchors")
    lines.append("```")
    return "\n".join(lines)


def render_tables(graph: dict) -> str:
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    node_rows = "\n".join(f"| {n['id']} | {n.get('label', '')} | {n.get('kind', '')} |" for n in nodes)
    edge_rows = "\n".join(
        f"| {e['from']} | {e['to']} | {e.get('label', '')} | {e.get('type', '')} |"
        for e in edges
    )

    return f"""## Nodes

| ID | Label | Kind |
|----|-------|------|
{node_rows}

## Edges

| From | To | Label | Type |
|------|----|-------|------|
{edge_rows}
"""


def render_markdown(graph: dict, source_name: str) -> str:
    frontmatter = {
        "graph_id": graph.get("graph_id"),
        "title": graph.get("title"),
        "description": graph.get("description"),
        "version": graph.get("version"),
        "generated_from": source_name,
        "generator": "docs/_tech_graph/scripts/graph_yaml_compile.py",
    }
    parts = [
        "---",
        yaml.dump(frontmatter).strip(),
        "---",
        "",
        f"# {graph.get('title')}",
        "",
        f"> {graph.get('description')}",
        "",
        f"> **源文件**：`{source_name}` · 由 `docs/_tech_graph/scripts/graph_yaml_compile.py` 生成 · 请勿直接手写本文件",
        "",
        render_mermaid(graph),
        "",
        render_tables(graph),
    ]
    return "\n".join(parts)


def main() -> int:
    yaml_files = sorted(GRAPH_DIR.glob("*.graph.yaml"))
    if not yaml_files:
        print("No .graph.yaml files found in", GRAPH_DIR, file=sys.stderr)
        return 1

    for yaml_path in yaml_files:
        md_path = yaml_path.with_suffix("").with_suffix(".md")
        raw = yaml_path.read_text(encoding="utf-8")
        graph = yaml.safe_load(raw)
        rendered = render_markdown(graph, yaml_path.name)
        md_path.write_text(rendered, encoding="utf-8")
        print(f"[GENERATED] {md_path.name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
