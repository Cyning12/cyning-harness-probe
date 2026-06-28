# Task：Probe · RAG hits=0 fallback 验收（示例）

> **状态**：draft  
> **freeze_id**：`HARNESS-PROBE-SAMPLE-V0.1`  
> **graph_delta**：`docs/_tech_graph/10_flow_rag.graph.yaml`  
> **test_strategy**：`recommended`  
> **orchestration**：`Cursor Task 链`  
> **git_branch**：`task/harness-probe-sample-rag`

### 人工闸 `human_gate`

| human_gate_id | status | blocks_hats | 说明 |
|---------------|--------|-------------|------|
| HG-TASK-DRAFT | approved | 22-R1,30 | 探针示例 |
| HG-AUDIT-R1 | approved | 30 | 探针示例 |

---

## 背景与目标

验证 Harness Probe 能否从本 task 编译 **AcceptanceContract**，并以 **RAG** 为入口裁剪 L0 子图。

---

## 范围

- [ ] 只读验证 Prompt 编译与 L1.5 运行时快照落盘
- [ ] 入口节点：`RAG` / 子图节点：`HIT0`

## 非范围

- 实际改码、git commit、调用真实 LLM

---

## 失败路径

| 触发条件 | 系统行为 | 可重试 | 用户可见 |
|----------|----------|--------|----------|
| hits == 0 | 走 OUT_NO_DATA → CTX fallback，仍可调 LLM 做不确定回答 | 否 | no_data 提示 |
| FTS RPC 超时 | rpc_execute_with_retry 退避后仍失败 | 是 · 最多 N 次 | 502 / RPC error |
| verify 命令非 0 | Lead BLOCKED，启动 fix-verify 子任务 | 否 | blocked + evidence |

---

## 验收标准

- [ ] `python -m src.probe compile --entry RAG` 生成 Prompt 且静态前缀含 `freeze_id`
- [ ] AcceptanceContract ≤ 3 行且含 F1/F2/F3
- [ ] L1.5 快照 JSON 写入 `outputs/`

---

## entry_node

`RAG`
