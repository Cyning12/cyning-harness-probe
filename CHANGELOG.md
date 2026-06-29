# Changelog

## v0.2 · 2026-06-29

### Added

- **PRE_SPAWN_VERIFY 校验**：新增 `python -m src.probe verify --task <path>` 子命令。
  - 校验 task 是否含 `human_gate` 表。
  - 校验 `blocks_hats` 含 `30` 时是否显式含 `HG-AUDIT-R1`。
  - 对齐工作区 IMP-09 / [`PROMPT_cursor_task_chain_serial_v1.md`](https://github.com/Cyning12/cyning-ink-workspace/blob/main/docs/harness/prompts/PROMPT_cursor_task_chain_serial_v1.md) §4.5。

### Changed

- **Prompt 生成层同步 workspace Harness V2.1 模板纪律**：
  - Subagent Prompt 明确禁止在业务 `*.graph.yaml` 写 `guardrails` / `token cap` / `max_retries`。
  - 明确 Subagent 只收 `AcceptanceContract` 表，不带 `failure_paths` 全文。
  - 30 / 40 帽必须回报 `failure_path_ref` 收工表。
- 单测新增 4 个 `human_gate` 校验用例。

### Commits

- `d641b1a` `feat(probe): sync with workspace Harness V2.1 templates · human_gate validation + PRE_SPAWN_VERIFY + prompt wording`

---

## v0.1 · 2026-06-28

### Added

- 初版 Probe CLI：`compile`、`graph-query`。
- L0 子图查询、L1 AcceptanceContract 编译、L2 Wiki 摘要注入。
- KV-Cache 友好三段式 Prompt 组装。
