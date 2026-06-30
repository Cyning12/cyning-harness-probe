# harness-probe 0.x 阶段总结（v0.1 → v0.7）

> 日期：2026-06-30  
> 范围：v0.1 / v0.2 / v0.3 / v0.4 / v0.5 / v0.6 / v0.7（含中间补丁）  
> 性质：文档归档，非代码变更

---

## 一、阶段总览

| 版本 | 日期 | 主题 | 关键交付 |
|------|------|------|----------|
| v0.1 | 2026-06-28 | 初版 Probe CLI | `compile`、`graph-query`、L0/L1/L2 三段式 Prompt |
| v0.2 | 2026-06-29 | PRE_SPAWN_VERIFY | `verify` 子命令、human_gate 校验、模板纪律 |
| v0.3 | 2026-06-29 | 全帽链 | 10-spec / 10-task / 20-review / 30 / 40 / 50-reinspect、`--run`、`--watch` |
| v0.4 | 2026-06-30 | SDK 重构 | `harness_sdk/` 无副作用核心库、`harness_probe/` CLI、包化 |
| v0.5 | 2026-06-30 | MCP Server | `harness_mcp/`、4 Tools + 1 Resource、可选依赖 `[mcp]` |
| v0.6 | 2026-06-30 | 真实执行器 | `--executor real`、SubprocessExecutor、max_retries、cwd |
| v0.7 | 2026-06-30 | 安全执行器 | CommandSafetyChecker、whitelist/audit/unsafe、dry-run、执行日志 |

---

## 二、各版本核心能力

### v0.1 · 编译探针雏形

- **目标**：验证 L0 图谱编译 + L1 验收合约 + L2 冷记忆能否组装成 KV-Cache 友好的 Subagent Prompt。
- **交付**：
  - `compile` 子命令
  - `graph-query` 子命令
  - 三段式 Prompt：`static_prefix` + `semi_static` + `dynamic_suffix`
- **局限**：仅支持 30/40 两顶帽子；无真实执行；无 MCP。

### v0.2 · 人闸与 PRE_SPAWN_VERIFY

- **目标**：在 30 改码前校验 task 人闸状态，防止未授权执行。
- **交付**：
  - `verify --task <path>` 子命令
  - 校验 `human_gate` 表是否存在
  - 校验 `blocks_hats` 含 `30` 时是否显式含 `HG-AUDIT-R1`
  - Prompt 模板纪律：禁止在 graph 写 guardrails / token cap / max_retries
- **意义**：建立 Harness 工作流的第一道机械门。

### v0.3 · 全帽链补齐

- **目标**：覆盖从 SPEC 草案到复检的完整任务生命周期。
- **交付**：
  - 10-spec：SPEC 草案 Prompt
  - 10-task：task 骨架 Prompt
  - 20-review：审核 Prompt + HG-AUDIT-R1 签收
  - 30 / 40：执行与审计帽
  - 50-reinspect：独立/全局双模式复检
  - `--run`：串行模拟执行并落盘 task_run JSON
  - `--watch`：freeze_id 漂移检测
- **意义**：形成完整的帽子流水线。

### v0.4 · SDK 重构与包化

- **目标**：将探针从脚本拆分为可复用 SDK + CLI 两层。
- **交付**：
  - `harness_sdk/`：models / compiler / builder / graph / runner
  - `harness_probe/`：CLI + IO
  - `pyproject.toml` 包化
  - 测试分层：`test_sdk_*.py` + `test_cli.py`
- **意义**：为后续 MCP、真实执行、安全执行奠定架构基础。

### v0.5 · MCP Server

- **目标**：让外部 Agent（如 Cursor / Claude Code）通过 MCP 调用探针能力。
- **交付**：
  - `harness_mcp/server.py` 基于 FastMCP
  - Tools：`probe_compile` / `probe_run` / `probe_audit` / `probe_verify`
  - Resource：`harness://freeze_id/current`
  - 可选依赖：`pip install -e ".[mcp]"`
- **意义**：探针从命令行工具升级为可被编排调用的服务。

### v0.6 · 真实执行器

- **目标**：让 contract.verify 从 dry-run 变为真实可执行。
- **交付**：
  - `SubprocessExecutor`
  - CLI `--executor {mock,real}`、`--max-retries`、`--cwd`
  - MCP `probe_run` 支持 `executor`、`max_retries`、`cwd`
  - `probe_audit` 识别 blocked 节点并给出 `next_hat="30"`
- **意义**：验收合约从纸面承诺进入可验证阶段。

### v0.7 · 安全执行器

- **目标**：为真实执行增加安全边界，防止危险命令误执行。
- **交付**：
  - `CommandSafetyChecker`（whitelist / audit / unsafe）
  - 危险字符黑名单、危险命令前缀黑名单、命令长度限制
  - `--dry-run` 预览模式
  - `execution_log_*.jsonl` 执行/拦截日志
  - `ExecutionResult` 新增 `blocked`、`dry_run`、`reason`
- **意义**：真实执行从"可用"变为"可放心用"。

---

## 三、架构演进

```text
v0.1  单文件脚本
  ↓
v0.2  + verify 人闸
  ↓
v0.3  + 全帽链 + run/watch
  ↓
v0.4  SDK(harness_sdk) + CLI(harness_probe) 分层
  ↓
v0.5  + MCP Server
  ↓
v0.6  + SubprocessExecutor 真实执行
  ↓
v0.7  + CommandSafetyChecker 安全执行
```

---

## 四、关键设计决策

| 决策 | 版本 | 说明 |
|------|------|------|
| 三段式 Prompt | v0.1 | 降低 KV-Cache 浪费，static 部分可复用 |
| human_gate 机械校验 | v0.2 | 30 改码前必须过闸 |
| 纯逻辑 Runner | v0.4 | `TaskRunner` 不读写文件，便于测试与 MCP 复用 |
| 可选 MCP 依赖 | v0.5 | 不强制所有用户安装 `mcp` 包 |
| executor 协议化 | v0.6 | `VerifyExecutor` 协议支持 mock/real/未来沙箱 |
| 默认 whitelist | v0.7 | 安全优先，unsafe 需 `HARNESS_UNSAFE=1` 二次确认 |

---

## 五、测试与质量基线

| 指标 | 当前值 |
|------|--------|
| 单测数量 | 49 passed |
| 代码检查 | ruff / mypy 全绿 |
| 图谱验证 | `graph-query --node CLI --depth 3` 21 nodes |
| 文档 | CHANGELOG / README / _tech_graph / task / invoke 齐全 |

---

## 六、经验教训

1. **任务单格式影响工具链**：v0.7 前 `@cyning/harness verify` 因反引号解析 bug 阻塞开工，已修复并沉淀 postmortem。
2. **安全不能事后补**：v0.6 真实执行后立刻在 v0.7 加安全校验，说明关键路径应先有安全设计。
3. **图谱与代码同步成本高**：v0.7 后立刻重建 `_tech_graph`，避免文档漂移。
4. **分层架构带来可测试性**：v0.4 SDK 重构后，CLI/MCP/Runner 可独立测试。

---

## 七、相关文档

- CHANGELOG：`../../CHANGELOG.md`
- README：`../../README.md`
- 技术图谱：`../../docs/_tech_graph/README.md`
- Phase 5 milestone：`../../docs/harness/invokes/PHASE5_MILESTONE_20260630_zh.md`
- 产品包 postmortem：`../../../cyning-harness/docs/methodology/execution/POSTMORTEM_backtick_gate_parsing_v1_zh.md`
