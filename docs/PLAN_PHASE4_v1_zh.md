# Phase 4 方案 · 真执行验证（verify_cmd runner · v0.6）

| 项 | 内容 |
| --- | --- |
| **状态** | `planning` |
| **版本** | v1 |
| **日期** | 2026-06-30 |
| **目标版本** | v0.6 |
| **触发** | v0.5 MCP Server 完成后，方法论中 "Verify 从 mock → 真跑" 进入可工程化阶段 |

---

## 1. 一句话目标

让 `probe_run` / `probe_audit` 不再只返回 mock pass，而是**真正执行 task 中 AcceptanceContract 的 `verify` 命令**，并支持失败重跑 / 打回 30 的短回路。

## 2. 当前问题

v0.5 的 `TaskRunner._mock_subagent_result` 固定返回：

```python
{"ref": "F1", "pass_fail": "pass", "evidence": "dry-run hat=30 · pytest tests/test_rag_fallback.py"}
```

这无法发现：
- `verify` 命令本身是否拼写错误
- 测试在真实仓库里是否真的通过
- failure_path 的触发条件是否可被复现

## 3. 目标态

```text
probe_run --executor real --from-hat 30 --to-hat 40
    → 对每个 contract 执行 verify_cmd
    → pass → evidence = stdout 摘要
    → fail → 进入 fix-verify 短回路（最多 N 次）
    → 仍 fail → run_node.status = blocked，recommendation = 打回 30
```

## 4. 关键设计

### 4.1 Executor 抽象

```python
class VerifyExecutor(Protocol):
    async def run(self, cmd: str, cwd: Path | None = None) -> ExecutionResult: ...

@dataclass
class ExecutionResult:
    returncode: int
    stdout: str
    stderr: str
    elapsed_ms: int

class SubprocessExecutor:
    async def run(self, cmd: str, cwd: Path | None = None) -> ExecutionResult:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return ExecutionResult(
            returncode=proc.returncode,
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
            elapsed_ms=...,
        )
```

### 4.2 TaskRunner 改造

- `TaskRunner.__init__` 增加 `executor: VerifyExecutor | None = None`
- `TaskRunner._execute_hat` 根据 `executor` 选择：
  - `None` → 保持原有 mock
  - `SubprocessExecutor` → 真实执行每个 contract 的 `verify`
- `TaskRunner.run_sequence` 增加 `max_retries: int = 0`（失败重跑次数）

### 4.3 CLI 参数

```bash
# 默认 mock（向后兼容）
python -m harness_probe.cli run --from-hat 30 --to-hat 40

# 真实执行（需显式授权）
python -m harness_probe.cli run --from-hat 30 --to-hat 40 --executor real --max-retries 2

# 指定工作目录
python -m harness_probe.cli run --executor real --cwd ../ai-ink-brain-api-python
```

### 4.4 MCP Tool 改造

`probe_run` 增加：
- `executor: str = "mock"`（可选 `"real"`）
- `max_retries: int = 0`
- `cwd: str | None = None`

### 4.5 安全边界

- 默认仍为 `mock=true` / `executor=mock`
- `--executor real` 需要调用方显式选择
- 不执行任何写入命令；只运行 `verify` 字段中声明的只读/测试命令
- 对 `verify` 命令做简单白名单：禁止 `rm`、`>`、`|` 等危险操作（可选）

## 5. 失败路径

| ID | 触发条件 | 系统行为 | 可重试 | 用户可见 |
| --- | --- | --- | --- | --- |
| F1 | `verify` 命令不存在 | returncode ≠ 0，evidence = stderr | 否 | CLI 报错 + audit fail |
| F2 | 测试运行超时 | TimeoutError → blocked | 可重试 | 重跑次数耗尽后 blocked |
| F3 | 命令输出过大 | 截断 stdout 至 4K | 是 | evidence 带截断标记 |
| F4 | 真实执行未授权 | `--executor real` 未指定但配置强制 | 拒绝运行 | 提示显式授权 |

## 6. 验收标准

- [ ] `python -m harness_probe.cli run --executor real` 真实执行 contract.verify 命令
- [ ] 失败时支持 `--max-retries` 重跑
- [ ] 重跑耗尽后 `run_node.status = blocked`
- [ ] `probe_audit` 对 blocked 节点输出 "打回至 30" 建议
- [ ] 默认 `--executor mock` 保持 v0.5 行为不变
- [ ] MCP `probe_run` 支持 `executor` / `max_retries` 参数
- [ ] 新增 `tests/test_sdk_executor.py` 覆盖 mock/real/timeout/重试

## 7. 依赖

- v0.5 MCP Server 已发布
- 需要测试仓库有真实的 `verify` 命令可执行（如 `pytest tests/ -q`）

## 8. 非范围

- 不接入 LLM 做修复（LLM fix 归 v0.8）
- 不执行 sandbox 隔离（sandbox 归 v0.8）
- 不改帽链语义
- 不改 graph.json

## 9. 修订记录

| 版本 | 日期 | 说明 |
| --- | --- | --- |
| v1 | 2026-06-30 | 初版 · verify_cmd runner + fix-verify 短回路 |
