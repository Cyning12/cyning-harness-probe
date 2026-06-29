# Changelog

## v0.3 · 2026-06-29

### Added

- **全帽链补齐**：`compile --hat` 支持 10-spec / 10-task / 20-review / 50-reinspect 四顶新帽。
  - `10-spec`：生成 SPEC 草案 Prompt（R0–R5、Delta、验收标准）。
  - `10-task`：生成 task 骨架 Prompt（SPEC→failure_paths 映射）。
  - `20-review`：生成审核 Prompt（approved/blocked + HG-AUDIT-R1 签收）。
  - `50-reinspect`：生成复检 Prompt（failure_path_ref 表 + independent/global 双模式）。
- **`--run` 模式**：`python -m src.probe run --from-hat 30 --to-hat 40` 串行模拟执行并落盘 task_run JSON。
- **`--watch` 模式**：`python -m src.probe watch --once` 检测 graph 与 task 的 freeze_id 漂移。
- **CLI 新增参数**：`--spec`（关联 SPEC）、`--review-target`（审核对象）、`--mode`（independent/global）、`--run-output`（关联运行记录）。

### Changed

- `builder.py`：重构为 `build_hat_prompt()` 分发函数；原 30/40 builder 保留。
- `orchestrator.py`：改用 `build_hat_prompt` + `handoff_summary`；支持 `from_hat`/`to_hat` 过滤。
- `models.py`：`HarnessTask` 新增 `spec_path`/`spec_text`/`review_target`/`run_output_path`/`reinspect_mode`。

### Commits

- `8b23630` `feat(phase1): full hat chain support · 10-spec/10-task/20-review/50-reinspect + --run + --watch`

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
