# Harness Probe · 框架 Q&A 落盘（v1）

> **日期**：2026-06-27  
> **关联**：[`README.md`](../README.md) · [`docs/ARCHITECTURE_v1_zh.md`](./ARCHITECTURE_v1_zh.md) · 工作区 [`COMPARISON_tech_graph…`](../../docs/harness/guides/COMPARISON_tech_graph_coding_wiki_graph_memory_v1_zh.md) §2.2

---

## Q1 · L0 如何设计？业务主导还是 Agent Core 先初版再自我进化？

**A · 先奠基，后进化（人机协同飞轮）**

| 阶段 | 谁主导 | 做什么 |
| --- | --- | --- |
| **第一步** | 业务 / 工程师 | L0 **初版骨架**：实体、流程、depends_on、锚点；Agent Core 只提供 **格式 + 查询接口**，不自动生成内容 |
| **第二步** | 设计时预留 | **进化协议**：Agent 如何提议改 L0（PR）、如何验证（export + harness verify）、谁审批（22 / human_gate） |
| **第三步** | 运行中 | 反思 → 提议 → 沙箱验证 → 人审 merge；**禁止** Agent 无 export 改 `graph.json` |

**面试句**：起点业务主导；框架标准化游乐场；进化靠运行经验 + 人审，不是黑盒自改。

---

## Q2 · Sub 之间如何共享？同一个 Seq 吗？

**A**

- **物理**：每个 Subagent **独立 Seq / request**，不共享 KV 显存。
- **逻辑**：Main 通过 **invoke 元数据 + 一行上一帽摘要** 传递业务上下文。
- **缓存策略**：L0 `freeze_id` 固定前缀 + System 放 Prompt **头部**，多 Sub 哈希相同 → 服务端 RadixAttention **可能**命中（非 Seq 继承）。

---

## Q3 · verify 失败后如何修复？

**A · 阻断 + 定向 fix + Resume**

1. `_run_verify` 非 0 → **BlockedError**，停止后续帽。  
2. Main 启动 **fix-verify Sub**（仅失败 ref + evidence 尾 + anchor）。  
3. 修复后 **重跑 verify_cmd**；绿则 Resume；仍红 → human_gate 通知 22。

对应工作区：[`PROMPT_cursor_task_chain_serial_v1.md`](../../docs/harness/prompts/PROMPT_cursor_task_chain_serial_v1.md) §5.4。

---

## Q4 · L2 合成摘要是给 Main 的交付物吗？

**A · 分时段**

| 时点 | 对象 | 作用 |
| --- | --- | --- |
| **执行中** | Subagent Prompt | `wiki.retrieve(top_k=3)` 冷启动，非 invoke 全文 |
| **关账后** | 未来 Agent / 人 | ingest 成 `syntheses/`，L2 冷资产 |

---

## Q5 · 自我进化未来交给一等 Agent？

**A · Agent 辅助治理，人仍最终闸**

- **审计员 Agent**（只读）：分析 drift / 失败日志 → 自动开 PR + impact_analysis。  
- **发布经理 Agent**（受限写）：仅低风险变更 + verify 全绿 + 22 gate → merge。  
- **结论**：分担提案与审查体力，**不是**取代 human_gate。

---

## Q6 · 中断重发涉及哪些技术？（扩展）

乐观锁 / draft 栈、Idempotency-Key、SSE Resumable、OT/CRDT（协作场景）——与 Harness 主链正交，可作 UX 专题。

---

## Q7 · 产品调度图谱 vs 任务执行图谱

**A · 双图谱模型**

| 维度 | L0 产品静态图 | L1.5 任务实例图 |
| --- | --- | --- |
| 类比 | 地铁线路图 | 本次导航轨迹 |
| 产生 | 开发/export | 运行时 Main 写 |
| 变异 | PR + CI + 22 | Agent 实时更新状态 |
| 归属 | 仓库资产 | user_id + session_id |

L0 回答「去哪调 RPC」；L1.5 回答「这次卡在哪、重试了几次」。  
关账后 L1.5 归档 → L2 Wiki 原料。

**本 Probe 落盘**：`outputs/task_run_<session>.json` 即 L1.5 示例。

---

## Q8 · 为什么要做临时 Agent（Probe）？

**A · Dogfooding + 第一份 L1.5 数据**

- 验证 L0 锚点、contract 编译、Prompt 静态/动态边界。  
- 不追求 UI / 真 LLM；**100 行 CLI** 即可。  
- 探针可销毁；L0 图纸 bug 提前暴露。

---

## Q9 · graph.json 在 Agent 上的作用？

**A**（见 COMPARISON §2.2）

- **角色**：L0 机器轨 · **graph_query 子图**，禁止整包灌 prompt。  
- **不是**：Runtime guardrails 执行器。  
- **与 Probe**：`graph-query` / `compile` 读同一份 graph_v2。

---

## 修订记录

| 日期 | 说明 |
| --- | --- |
| 2026-06-29 | v1.1 · 同步 workspace Harness V2.1 模板 · 新增 `verify` 命令 · human_gate 校验 · Prompt 纪律更新 · 版本 bump v0.2 |
| 2026-06-27 | v1 · 落盘对话摘要 + 与工作区 Harness 交叉引用 |
