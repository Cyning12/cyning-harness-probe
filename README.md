# Harness Probe

> **Harness 探针工程** — 验证 L0 图谱编译 + L1 验收合约 + L2 冷记忆 + KV-Cache 友好 Prompt 组装。  
> **不是** Agent 产品 Runtime；dry-run 为主，无真实 LLM 调用。  
> **当前版本**：**v0.2** · 见 [`CHANGELOG.md`](./CHANGELOG.md)

**仓库**：https://github.com/Cyning12/cyning-harness-probe · `git@github.com:Cyning12/cyning-harness-probe.git`

## 快速开始

```bash
cd harness-probe
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 编译 Prompt + 生成 L1.5 快照（dry-run）
python -m src.probe compile --task data/tasks/sample_task.md --entry RAG

# L0 子图查询
python -m src.probe graph-query --node RAG --depth 2

# 测试
pytest tests/ -q
```

## 输出

| 路径 | 含义 |
| --- | --- |
| `outputs/prompt_<session>_hat30.md` | 某帽完整 Subagent Prompt |
| `outputs/task_run_<session>.json` | **L1.5** 任务执行实例图 |

## 使用 Ink 全量图谱

```bash
python -m src.probe compile \
  --graph ../ai-ink-brain-api-python/docs/_tech_graph/graph.json \
  --task data/tasks/sample_task.md \
  --entry RAG
```

## 文档

- [方法论定位（推荐阅读）](docs/METHODOLOGY_v1_zh.md)
- [框架 Q&A 落盘](docs/QA_AND_FRAMEWORK_v1_zh.md)
- [架构 v1](docs/ARCHITECTURE_v1_zh.md)
- 工作区对照（Ink monorepo）：`docs/harness/guides/COMPARISON_tech_graph_coding_wiki_graph_memory_v1_zh.md` §2.2

## 在方法论中的位置

Probe 是 **完整 Harness 的编译链子集**（非 Agent 产品、非 Runtime）。未来可并入 Agent 产品的 **Harness SDK**（`compile_context` + contract + L1.5）。详见 [`docs/METHODOLOGY_v1_zh.md`](docs/METHODOLOGY_v1_zh.md)。

## 设计哲学

**大脑（LLM）负责推理，Harness（Core）负责托底。**

```text
L0 静态图（仓库）  +  L1.5 动态轨迹（会话）  +  L1 合约（task）  +  L2 摘要（Wiki）
         ↓                      ↓
    graph_query              task_run JSON
         ↓                      ↓
              Subagent Prompt（三段式）
```

## License

MIT · 源自 Ink 工作区 Harness 实验，独立维护
