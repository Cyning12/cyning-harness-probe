#!/usr/bin/env python3
"""graph_json_export.py · 从 .graph.yaml 合并生成 graph.json（graph_v2 兼容）"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml


GRAPH_DIR = Path(__file__).resolve().parent.parent


def main() -> int:
    yaml_files = sorted(GRAPH_DIR.glob("*.graph.yaml"))
    if not yaml_files:
        print("No .graph.yaml files found in", GRAPH_DIR, file=sys.stderr)
        return 1

    nodes: list[dict] = []
    edges: list[dict] = []
    seen_node_ids: set[str] = set()
    seen_edges: set[tuple[str, str, str]] = set()

    for yaml_path in yaml_files:
        raw = yaml_path.read_text(encoding="utf-8")
        graph = yaml.safe_load(raw)

        for node in graph.get("nodes", []):
            nid = node["id"]
            if nid in seen_node_ids:
                continue
            seen_node_ids.add(nid)
            nodes.append(
                {
                    "id": nid,
                    "label": node.get("label", nid),
                    "kind": node.get("kind", "flow"),
                    "module_id": nid,
                    "graph_id": "probe",
                }
            )

        for edge in graph.get("edges", []):
            key = (edge["from"], edge["to"], edge.get("label", ""))
            if key in seen_edges:
                continue
            seen_edges.add(key)
            edges.append(
                {
                    "from": edge["from"],
                    "to": edge["to"],
                    "mark": edge.get("label", "->") if not edge.get("mark") else edge.get("mark"),
                    "type": edge.get("type", "depends_on"),
                    "label": edge.get("label", ""),
                    "graph_id": "probe",
                    "anchors": edge.get("anchors", []),
                }
            )

    output = {
        "schema_version": "graph_v2",
        "freeze_id": "HARNESS-PROBE-GRAPH-V2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "nodes": nodes,
        "edges": edges,
    }

    out_path = GRAPH_DIR / "graph.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[EXPORTED] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
