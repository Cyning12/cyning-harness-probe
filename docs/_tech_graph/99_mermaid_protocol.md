# 99_mermaid_protocol · 图谱维护协议

> **用途**：维护者改拓扑时的操作顺序。

## 双轨制

| 文件 | 角色 | 编辑方式 |
|------|------|----------|
| `.graph.yaml` | **源文件**（机器/AI 可读） | 手工编辑 |
| `.md` | 人类友好版（含 Mermaid + 表格） | 由脚本生成 |
| `graph.json` | graph_v2 导出产物 | 由脚本生成 |

## 维护步骤

1. 修改对应 `.graph.yaml` 的 nodes / edges
2. 运行 `python docs/_tech_graph/scripts/graph_yaml_compile.py` 重新生成 `.md`
3. 运行 `python docs/_tech_graph/scripts/graph_json_export.py` 重新生成 `graph.json`
4. 运行 `python -m harness_probe.cli graph-query --graph docs/_tech_graph/graph.json --node CLI --depth 3` 验证子图完整性
5. 更新本文件修订记录

## 修订记录

| 日期 | 说明 |
| --- | --- |
| 2026-06-29 | v1 · 手工创建 8 节点 13 边（.ai.md 单文件真值） |
| 2026-06-30 | v2 · 迁移为 `.graph.yaml` + `.md` 双轨；同步 v0.5 模块结构（harness_sdk / harness_probe / harness_mcp） |
