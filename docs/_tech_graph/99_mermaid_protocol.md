# 99_mermaid_protocol · 图谱维护协议

> **用途**：维护者改拓扑时的操作顺序。手工维护阶段（Phase 1），自动导出后（Phase 2）。

## 手工维护（当前）

1. 修改对应 `.ai.md` 的 nodes / edges 节
2. 同步更新 `graph.json`
3. 运行 `python -m src.probe graph-query --graph docs/_tech_graph/graph.json --node CLI --depth 3` 验证子图完整性
4. 更新本文件修订记录

## 自动导出（Phase 2 · 目标态）

1. 修改 `.ai.md`
2. 运行 `python tools/tech_graph_graph_query.py --export`（TBD）
3. CI `manifest_check` 拦截漂移

## 修订记录

| 日期 | 说明 |
| --- | --- |
| 2026-06-29 | v1 · 手工创建 8 节点 13 边 |
