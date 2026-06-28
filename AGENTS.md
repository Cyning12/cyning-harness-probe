# Harness Probe · Agent 入口

Open Folder = **`harness-probe/`**（本目录）。

## 读序

1. [`README.md`](README.md)
2. [`docs/METHODOLOGY_v1_zh.md`](docs/METHODOLOGY_v1_zh.md)
3. [`docs/QA_AND_FRAMEWORK_v1_zh.md`](docs/QA_AND_FRAMEWORK_v1_zh.md)
4. [`docs/ARCHITECTURE_v1_zh.md`](docs/ARCHITECTURE_v1_zh.md)

## 命令

```bash
python -m src.probe compile --task data/tasks/sample_task.md
pytest tests/ -q
```

## 边界

- **不**在业务 graph JSON 加 `guardrails` / token cap
- **不**替代 `@cyning/harness verify`（未来可 shell out）
- L0 真值仍以各仓 `*.graph.yaml` export 为准

## 上游对照（Ink 工作区 · 可选）

- `COMPARISON_tech_graph_coding_wiki_graph_memory_v1_zh.md` §2.2
- `PROMPT_cursor_task_chain_serial_v1.md` v1.1
