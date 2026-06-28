# Harness Probe · 方法论定位（v1）

> **日期**：2026-06-27  
> **读者**：维护者 · 面试叙事 · 对外文章  
> **关联**：[`QA_AND_FRAMEWORK_v1_zh.md`](./QA_AND_FRAMEWORK_v1_zh.md) · [`ARCHITECTURE_v1_zh.md`](./ARCHITECTURE_v1_zh.md)  
> **上游方法论**：《AI 编程可闭环协作》双轨 + ICV；Ink 工作区 `COMPARISON_tech_graph…` §2.2 · `PROMPT_cursor_task_chain_serial_v1.md` v1.1

---

## 1. 一句话定位

**Harness Probe** 不是 Agent 产品，而是 **仓库级 SDD Harness** 里的 **Context Compiler + Acceptance Compiler + Dry-run Orchestrator（编译探针）**：

- 输入：`graph_v2` + `task.md` + Wiki 摘要 stub  
- 输出：Subagent 注入 Prompt + **L1.5** 任务实例 JSON + 可度量的 static/dynamic 比  

它在方法论里验证的是：**Inform 能否被编译、Constrain 能否在派工边界机械执行、Verify 能否对照 contract**——而不是 LLM 会不会写代码。

---

## 2. 在「Model + Harness = Agent」里的坐标

行业公式（如 DeepSeek Agent Harness 岗）：

```text
Agent = Model（推理） + Harness（驾驭 / 约束 / 上下文 / 验收）
```

本工作区 **刻意拆分**：

| 层 | 谁做 | Probe v0.1 |
| --- | --- | --- |
| **Model** | 厂商 LLM | **不碰** |
| **Runtime Harness** | Kimi / Claude / Cursor Host（step、retry、token、sandbox） | **不碰、不伪造** |
| **SDD Harness（过程 + 结构）** | task · 图谱 · verify · 人闸 · 帽链 | **Probe 只实现其中一条「编译链」** |

**对外口径**：

> Model + **Runtime** Harness = 厂商 Agent 产品  
> **cyning Harness** = 过程纪律 + 结构 Inform（与 Runtime **互补**）  
> **Harness Probe** = 上述 Harness 的 **奠基期验证探针**（Dogfooding）

---

## 3. Probe 只是 Harness 的一部分——未来可并入完整 Agent Harness

**是。** 当前 Probe **不是** Harness 全集，而是 **可独立运行、可测试的最小切片**：

```text
完整 Agent Harness（目标态）
├── Runtime envelope（Host · 未来与 agent-core 对齐）
├── 过程轨编排（00→22→30→40→50 · PROMPT 链）
├── 结构轨 Inform（graph_query · manifest · drift_check）
├── L2 编译叙事（Wiki ingest）
├── Verify 门禁（@cyning/harness verify · CI）
└── 【Probe 已实现的子集】
      ├── graph 子图裁剪
      ├── failure_paths → AcceptanceContract
      ├── 三段式 Prompt 组装
      ├── human_gate / pre_spawn 硬闸（dry-run）
      └── L1.5 task_run 快照
```

**演进路径**：

| 阶段 | 形态 | 关系 |
| --- | --- | --- |
| **v0.1（现在）** | 独立 CLI 仓 `cyning-harness-probe` | 验证编译链 · 不依赖 LLM |
| **v0.2** | + `harness verify` shell out · 真 verify_cmd | 与工作区 npm 包对齐 |
| **v0.3+** | 作为 **库 / MCP Tool** 嵌入 Cursor/Kimi 编排层 | Probe 模块进 **完整 Agent 的 Harness 层** |
| **目标态** | Agent 产品内 **Harness SDK** 的一翼 | Model 仍外置；Harness 含 Runtime + SDD 两域 |

Probe 代码 **不必推倒重来**：`graph_loader` · `compiler` · `builder` · `orchestrator` 可直接迁为 `cyning-harness` 或 agent-core 旁的 **`harness.context`** 包。

---

## 4. Probe 算什么？工具、产品、还是模块？

在「长期做 Agent 的 **Harness 部分**」前提下，建议 **三层命名**（避免只说「小工具」贬义，也避免过早叫「平台」）：

| 称谓 | 含义 | 适用场景 |
| --- | --- | --- |
| **验证探针（Probe）** | 奠基期 **Dogfooding 仪器** | 现在 v0.1 · README · 面试「正式产品前做了什么验证」 |
| **编译器模块（Compiler Module）** | Harness 的 **可复用子系统** | 技术设计 · 并入完整 Agent 时的包名 |
| **Harness SDK 能力（Future）** | 对外 **`compile_context(task, graph)`** API | 目标态 · 与 Runtime envelope 并列 |

**推荐表述**：

- **现在**：Probe = **方法论验证探针** + **Harness 编译链 reference implementation**  
- **不是**：又一个 ChatBot、不是 Runtime、不是 L0 真源  
- **未来**：同一套逻辑成为 **完整 Agent Harness 的 Inform/Constrain 编译子层**（SDK 或 Host 插件）

与 `@cyning/harness`（npm · task 字段 / verify CLI）关系：

| 组件 | 方法论职责 |
| --- | --- |
| `@cyning/harness` | **Constrain + Verify 门禁**（拒开工、字段校验） |
| **Harness Probe** | **Inform 编译 + 派工 Prompt 物化 + L1.5 轨迹** |
| 帽链 PROMPT | **过程轨编排**（人 + Lead Agent） |
| 未来 **合一** | `verify` + `compile` + `orchestrate` 同一 Harness SDK |

---

## 5. 双轨 + ICV 对照

### 5.1 结构轨 vs 过程轨

| 轨道 | 回答什么 | Probe 触点 |
| --- | --- | --- |
| **结构轨** | 改哪里、影响谁 | `graph-query` · Prompt 内 L0 子图 |
| **过程轨** | 谁做、何时合、如何验 | contract 表 · gate_scan · task_run JSON |

### 5.2 Inform – Constrain – Verify

| 支柱 | Probe v0.1 |
| --- | --- |
| **Inform** | 子图 + contract + Wiki top_k |
| **Constrain** | human_gate BLOCKED · 无 contract 拒编译 |
| **Verify** | evidence / failure_path_ref 表（mock → 未来真跑） |

### 5.3 双图谱

| 层 | 对象 | 生命周期 |
| --- | --- | --- |
| **L0** | `graph.json` | 仓库 · PR + export |
| **L1.5** | `task_run_*.json` | 会话 · 用户资产 · Wiki 原料 |
| **L1** | AcceptanceContract | task 编译 · Subagent 注入 |
| **L2** | Wiki 摘要 | 关账 ingest（Probe 用 stub） |

---

## 6. 设计理念（五条）

1. **大脑推理，Harness 托底** — LLM 写码；Probe 编译上下文与验收面。  
2. **结构压缩 + 验收压缩** — 子图非整包；failure_paths 非全文；static ratio 可度量。  
3. **双图谱** — L0 宪法 vs L1.5 行程单。  
4. **先奠基，后进化** — L0 人主导 + PR；Agent 只提议不黑盒改图。  
5. **与 Runtime 分域** — 不在业务 graph 写 guardrails / token cap。

---

## 7. 长期方向（与 AI Coding 实践的关系）

你的理论在 **AI Coding** 场景持续迭代；Probe 是 **把理论钉在可运行代码上** 的第一步。

```text
AI Coding 实践（Ink · kimi fork · Harness 帽链）
        ↓ 抽象
方法论（双轨 · ICV · 图谱消费 · 人闸）
        ↓ 最小可运行证明
Harness Probe（编译探针 · 本仓）
        ↓ 模块化
Harness SDK 编译子层（并入 Agent 产品 Harness）
        ↓ 与 Model 组合
Model + Harness = Agent（招聘叙事上的目标态）
```

**关键**：长期做 **Harness 部分**，不是要做 **Foundation Model**；Probe 证明的是 **「驾驭层」里 Inform 编译与验收预演** 可以工程化。

---

## 8. 话术模板

**30 秒**  
Harness Probe 是 SDD Harness 的编译探针：把 L0 子图和 task 失败路径压成 Subagent 注入包，并落 L1.5 执行快照；不碰 LLM Runtime。

**面试**  
完整 Agent 需要 Model 和 Harness。我们长期做 **仓库级 Harness**；Probe 是当前 **Compiler 模块的 reference implementation**，未来并入 Host 编排层，与 Runtime envelope 并列。

**边界**  
Probe 不是 Agent Core、不是 L0 真源、不替代 22 人审；是 **奠基期仪器**，验证「敢合并」之前的编译链可跑通。

---

## 修订记录

| 日期 | 说明 |
| --- | --- |
| 2026-06-27 | v1 · 方法论定位 · Probe 与完整 Harness / Agent 关系 |
