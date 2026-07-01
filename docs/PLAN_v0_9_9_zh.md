# v0.9.9 / pre-1.0.0 规划 · LLM Provider 集成验证

> 日期：2026-06-30  
> 类型：预发布验证版规划  
> 目标：在 v1.0.0 正式发布前，先接入真实 LLM 并在 cyning-harness 与 ai-ink-brain-api-python 两个真实项目中验证，不对外发布正式 tag

---

## 一、版本定位

v0.9.9 是 v1.0.0 前的**预发布验证版本**。它在 v0.9.2 配置增强之后，把 LLM 作为可选 Provider 插件接入 harness-probe，但不默认启用、不发布 GitHub Release。

只有经过真实项目验证，并满足冻结标准后，才决定是否将 LLM 能力纳入 v1.0.0。

---

## 二、为什么 LLM 不在 harness-probe 核心中

根据 `CLAUDE.md` 约束：

> **不接入真实 LLM**  
> **不改 cyning-harness 产品仓代码**

因此 LLM 能力必须以**可选插件**形式存在，且默认关闭。harness-probe 核心仍然是"编译 + 执行 + 安全 + 审计"的本地工具。

---

## 三、LLM Provider 设计

### 3.1 新增模块

```
harness_sdk/
  llm/
    __init__.py
    base.py              # LLMProvider 协议
    models.py            # LLMRequest / LLMResponse
    openai_provider.py   # OpenAI / 兼容 API
    anthropic_provider.py# Anthropic Messages API
    local_provider.py    # llama.cpp / vLLM / Ollama（OpenAI 兼容 endpoint）
  executor_plugins/
    llm_executor.py      # 用 LLM 判断 contract 是否通过
```

### 3.2 LLMProvider 协议

```python
class LLMProvider(Protocol):
    async def generate(self, request: LLMRequest) -> LLMResponse: ...
    def describe(self) -> str: ...
```

### 3.3 LLMExecutor

- 接收 `contract.verify` 作为 prompt
- 构造 few-shot 模板：
  - 给出 contract 的 trigger / expected
  - 要求 LLM 返回 JSON：`{"result": "pass|fail|uncertain", "reason": "..."}`
- 返回 `ExecutionResult`（dry_run=False，但由 LLM 生成 returncode）
- 所有 LLM 调用写入审计日志

### 3.4 配置

`config/llm.yaml`：

```yaml
provider: openai
model: gpt-4o-mini
base_url: https://api.openai.com/v1
api_key_env: OPENAI_API_KEY
temperature: 0.0
max_tokens: 512
timeout: 30
```

### 3.5 可选依赖

```toml
[project.optional-dependencies]
llm = ["openai>=1.0", "anthropic>=0.30"]
```

---

## 四、下游项目接入方式

### 4.1 cyning-harness 产品仓（Host 层）

**定位**：cyning-harness 调用 harness-probe 的 CLI/SDK，再决定是否启用 LLM Executor。

**接入方式**：

1. 在 cyning-harness 中安装 `pip install cyning-harness-probe[llm]`
2. 配置 `config/llm.yaml` 和 `config/executor.yaml`：
   ```yaml
   # executor.yaml
   default_plugin: llm
   ```
3. 调用：
   ```python
   from harness_sdk.runner import TaskRunner
   from harness_sdk.llm import load_llm_provider

   runner = TaskRunner(
       task=task,
       executor=LLMExecutor(provider=load_llm_provider("config/llm.yaml")),
   )
   ```
4. 验证场景：
   - 用 LLM 自动判断"验收合同是否通过"
   - 对无法本地验证的合同（如"代码风格是否符合约定"），用 LLM 做语义判断

### 4.2 ai-ink-brain-api-python 后端（工具调用层）

**定位**：后端 API 在 RAG/ingest 流程中调用 harness-probe 的 LLM Executor，生成或判断验收命令。

**接入方式**：

1. 后端 `pyproject.toml` 添加 `cyning-harness-probe[llm]` 依赖
2. 提供 API endpoint `/api/v1/harness/run`：
   - 接收 task_id、contract_id
   - 用 LLM Executor 生成 verify 命令
   - 再调用 `SubprocessExecutor` 或 `DockerExecutor` 沙箱执行
3. 验证场景：
   - LLM 生成 pytest 命令验证新接口
   - LLM 判断 RAG 检索结果是否满足合同要求

---

## 五、验证与冻结标准

### 5.1 验证阶段

| 阶段 | 周期 | 目标 |
|------|------|------|
| 阶段 1 | 1 周 | 在 cyning-harness 中跑通 LLM Executor 判断合同 |
| 阶段 2 | 1 周 | 在 ai-ink-brain-api-python 中跑通 LLM 生成 + 沙箱执行 |
| 阶段 3 | 3-5 天 | 收集成本、延迟、错误率数据 |
| 阶段 4 | 3-5 天 | 决定是否纳入 v1.0.0，以及默认/可选策略 |

### 5.2 冻结标准

- [ ] 2 个真实项目运行 2 周无 P0/P1 bug
- [ ] LLM 调用成本可接受（单次 contract 判断 < $0.01）
- [ ] 平均延迟 < 5s（本地模型可放宽）
- [ ] 审计日志覆盖所有 LLM 调用
- [ ] 明确 v1.0.0 中 LLM Executor 是默认组件还是可选组件

### 5.3 失败路径

| 触发条件 | 系统行为 | 是否可重试 | 用户可见 |
|----------|----------|------------|----------|
| LLM API 超时 | 返回 `uncertain` 状态，记录错误 | 是 | 警告 |
| LLM 返回不可解析 JSON | 返回 `fail` 状态，记录原始输出 | 否 | 错误提示 |
| API Key 缺失 | 初始化失败，提示设置环境变量 | 是 | 明确错误 |
| 成本超出阈值 | 拦截调用，提示升级配置 | 否 | 错误提示 |

---

## 六、与 v1.0.0 关系

- v0.9.9 验证通过后，v1.0.0 可以正式包含 LLM Provider（可选或默认）
- 若验证不通过，v1.0.0 仍发布，但 LLM 能力推迟到 v1.1.0
- v1.0.0 的"生产就绪"不以 LLM 集成为前提

---

## 七、任务单建议

后续创建：`docs/harness/tasks/active/task_harness_probe_v0_9_9_llm_provider_v1.md`
