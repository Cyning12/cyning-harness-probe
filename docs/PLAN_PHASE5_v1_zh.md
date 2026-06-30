# Phase 5 方案 · 安全执行与命令白名单（v0.7）

| 项 | 内容 |
| --- | --- |
| **状态** | `planning` |
| **版本** | v1 |
| **日期** | 2026-06-30 |
| **目标版本** | v0.7 |
| **触发** | v0.6 已实现真实子进程执行，但缺少安全边界；需在 sandbox 之前建立命令白名单与执行日志机制 |

---

## 1. 一句话目标

让 `--executor real` 从「显式授权即执行」升级为「**先校验、再预览、后执行、全记录**」，在不引入完整 sandbox 的前提下，拦截危险命令、提供 dry-run 预览、并落盘执行日志。

---

## 2. 当前问题

v0.6 的 `SubprocessExecutor` 直接通过 `asyncio.create_subprocess_shell` 执行 `contract.verify`：

```python
proc = await asyncio.create_subprocess_shell(cmd, ...)
```

风险：
- `verify` 字段可能包含 `rm -rf`、`>` 重定向、`|` 管道等破坏性操作
- 真实执行前没有预览通道，调用方无法确认即将运行的命令
- 执行结果只写入 `task_run_*.json`，缺少独立的、按时间排序的**执行日志**
- MCP / CLI 调用方难以区分「命令被拒绝」与「命令执行失败」

---

## 3. 目标态

```text
probe_run --executor real --from-hat 30 --to-hat 40
    → 解析每个 contract.verify
    → 白名单校验（禁止 shell 元字符、危险命令、写入操作）
    → 可选 --dry-run 输出待执行命令列表
    → 真实执行（超时、截断、cwd）
    → 结果写入 task_run_*.json + execution_log_*.jsonl
```

---

## 4. 关键设计

### 4.1 命令安全模型

采用**默认拒绝 + 显式白名单**策略：

| 类别 | 默认行为 | 可配置 |
| --- | --- | --- |
| 纯读取命令 | 允许 | `allowed_read_commands: list[str]` |
| 测试命令 | 允许 | `allowed_test_commands: list[str]` |
| 危险 shell 元字符 | 拒绝 | 不可覆盖 |
| 重定向 / 管道 / 后台 | 拒绝 | 不可覆盖 |
| 文件系统写入 | 拒绝 | 不可覆盖 |

### 4.2 危险字符黑名单（不可覆盖）

```python
DANGEROUS_SHELL_METACHARACTERS = {
    ";", "&", "|", "`", "$", "(", ")", "{", "}", "<", ">", "*", "?", "~", "!",
}
```

> 仅允许空格分隔的简单命令 + 参数，如 `pytest tests/test_rag_fallback.py -q`。

### 4.3 危险命令前缀黑名单（不可覆盖）

```python
DANGEROUS_COMMAND_PREFIXES = {
    "rm", "mv", "cp", "dd", "mkfs", "chmod", "chown", "sudo", "su",
    "curl", "wget", "ssh", "scp", "sftp", "ftp", "telnet", "nc", "netcat",
}
```

### 4.4 白名单配置

新增 `config/probe_config.yaml` 字段：

```yaml
executor:
  safety:
    mode: "whitelist"  # whitelist | audit | disabled
    allowed_read_commands:
      - "ls"
      - "cat"
      - "echo"
      - "find"
      - "git status"
      - "git diff"
      - "git log"
    allowed_test_commands:
      - "pytest"
      - "python -m pytest"
      - "python -m unittest"
      - "ruff check"
      - "mypy"
    max_command_length: 1024
```

- `mode: whitelist`：必须通过白名单 + 黑名单校验
- `mode: audit`：只记录警告，不阻止执行（用于过渡）
- `mode: disabled`：完全关闭安全校验（**不推荐**，需环境变量 `HARNESS_UNSAFE_EXECUTOR=1` 二次确认）

### 4.5 `--dry-run` 预览

CLI / MCP 新增 `--dry-run` 参数：

```bash
python -m harness_probe.cli run --executor real --dry-run --from-hat 30 --to-hat 40
```

输出：

```text
[Dry-run] 将执行以下命令（不实际运行）：
  30 · F1 · pytest tests/test_rag_fallback.py -q
  40 · F1 · pytest tests/test_rag_retrieval.py -q
```

### 4.6 执行日志落盘

新增 `outputs/execution_log_<session>.jsonl`，每行一条：

```json
{"ts": "2026-06-30T08:20:24.408614+00:00", "session_id": "abc123", "hat": "30", "ref": "F1", "cmd": "pytest tests/test_rag_fallback.py -q", "cwd": "/Users/cyning/Projects/ai-ink-brain-api-python", "allowed": true, "returncode": 0, "elapsed_ms": 1234, "truncated": false}
```

若被安全拦截：

```json
{"ts": "2026-06-30T08:20:24.408614+00:00", "session_id": "abc123", "hat": "30", "ref": "F1", "cmd": "rm -rf /", "allowed": false, "reason": "dangerous_command_prefix: rm"}
```

### 4.7 SDK 改造

新增 `harness_sdk/safety.py`：

```python
class CommandSafetyChecker:
    def __init__(self, config: SafetyConfig | None = None): ...
    def check(self, cmd: str) -> SafetyResult: ...

@dataclass
class SafetyResult:
    allowed: bool
    reason: str | None = None
    mode: str = "whitelist"
```

`SubprocessExecutor` 改造：

```python
class SubprocessExecutor:
    def __init__(
        self,
        timeout: float = 60.0,
        max_stdout: int = 4096,
        safety: CommandSafetyChecker | None = None,
        dry_run: bool = False,
        log_sink: ExecutionLogSink | None = None,
    ): ...
```

执行流程：

1. `safety.check(cmd)` → 不通过则返回 `ExecutionResult(returncode=-2, stderr=reason, blocked=True)`
2. `dry_run=True` → 返回 `ExecutionResult(returncode=0, stdout="[dry-run]", dry_run=True)`
3. 真实执行 → 写 log → 返回结果

### 4.8 CLI / MCP 参数

CLI `run` 新增：

```bash
--dry-run              # 预览模式
--safety-mode          # whitelist | audit | disabled
--execution-log-dir    # 执行日志目录，默认 outputs/
```

MCP `probe_run` 新增同名字段。

---

## 5. 失败路径

| ID | 触发条件 | 系统行为 | 可重试 | 用户可见 |
| --- | --- | --- | --- | --- |
| S1 | 命令含危险 shell 元字符 | `returncode=-2`，`blocked=True`，reason=metacharacter | 否 | CLI 报错 + audit fail |
| S2 | 命令前缀在黑名单 | `returncode=-2`，`blocked=True`，reason=dangerous_command_prefix | 否 | CLI 报错 + audit fail |
| S3 | 命令不在白名单 | `returncode=-2`，`blocked=True`，reason=not_in_whitelist | 否 | 提示更新 `probe_config.yaml` |
| S4 | 命令超长 | `returncode=-2`，reason=command_too_long | 否 | 提示缩短命令 |
| S5 | dry-run 模式 | `returncode=0`，`dry_run=True`，不执行 | 是 | 输出预览列表 |
| S6 | audit 模式 | 执行但记录 warning | 是 | 日志带 `allowed=true` + `audit_warning` |
| S7 | unsafe 模式未二次确认 | 拒绝执行 | 否 | 提示设置 `HARNESS_UNSAFE_EXECUTOR=1` |

---

## 6. 验收标准

- [ ] `SubprocessExecutor` 默认启用白名单安全校验
- [ ] 危险字符 / 危险命令前缀被拦截并返回明确 reason
- [ ] `--dry-run` 输出待执行命令列表而不实际运行
- [ ] 真实执行结果写入 `outputs/execution_log_<session>.jsonl`
- [ ] 拦截事件也写入 execution log
- [ ] MCP `probe_run` 支持 `dry_run`、`safety_mode` 参数
- [ ] 新增 `tests/test_sdk_safety.py` 覆盖白名单 / 黑名单 / dry-run / audit / unsafe 模式
- [ ] 新增 CLI 端到端测试覆盖 `--dry-run` 与危险命令拦截
- [ ] README 与 CHANGELOG 更新

---

## 7. 依赖

- v0.6 真实执行器已发布
- 需要设计 `config/probe_config.yaml` 的安全配置段

---

## 8. 非范围

- 不引入 Docker / nsenter / seccomp 等完整 sandbox（归 v0.8）
- 不做命令语义级分析（如解析 `pytest` 参数合法性）
- 不接入 LLM 自动修复被拦截命令
- 不改帽链语义与 graph.json

---

## 9. 修订记录

| 版本 | 日期 | 说明 |
| --- | --- | --- |
| v1 | 2026-06-30 | 初版 · 安全执行 + 命令白名单 + dry-run + 执行日志 |
