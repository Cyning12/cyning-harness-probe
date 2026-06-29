# Phase 1 实施计划 · 补齐全帽链（v1）

| 项 | 内容 |
| --- | --- |
| **状态** | `planning` |
| **版本** | v1 |
| **日期** | 2026-06-29 |
| **范围** | Harness Probe Phase 1：补齐 10-spec / 10-task / 20-review / 50-reinspect 四顶帽子 + `--run` 模拟执行 + `--watch` freeze_id 漂移检测 |
| **前置** | Probe v0.2 已发布 · `src/compiler.py` / `src/builder.py` / `src/orchestrator.py` 已具备 30/40 编译能力 |

---

## 1. 总体目标

在 **1 周内**完成：

1. `python -m src.probe compile --hat 10-spec` 可生成 SPEC 起草帽 Prompt
2. `python -m src.probe compile --hat 10-task` 可生成 task 需求帽 Prompt
3. `python -m src.probe compile --hat 20-review` 可生成 task/spec 审核帽 Prompt
4. `python -m src.probe compile --hat 50-reinspect` 可生成独立复检/全局验收帽 Prompt
5. `python -m src.probe run --task ... --from-hat 30 --to-hat 40` 可串行模拟执行并落盘 `task_run.json`
6. `python -m src.probe watch --graph ... --task ...` 可监控 freeze_id 漂移

---

## 2. 当前 30/40 实现保留

现有命令不变：

```bash
python -m src.probe compile --task data/tasks/sample_task.md --entry RAG --hat 30
python -m src.probe compile --task data/tasks/sample_task.md --entry RAG --hat 40
```

内部通过 `src/builder.py::build_subagent_prompt()` 生成三段式 Prompt。新增帽子沿用同一 builder，但 `semi_static` / `dynamic_suffix` 按帽职责替换。

---

## 3. 新增帽子详细设计

### 3.1 10-spec · SPEC 需求起草帽

**命令**

```bash
python -m src.probe compile \
  --task data/tasks/sample_task.md \
  --entry RAG \
  --hat 10-spec
```

**输入**

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `--task` | Path | task.md 路径（含 `## 背景与目标`、`## 范围`） |
| `--entry` | str | 入口图谱节点，用于裁剪 L0 子图 |
| `--hat` | "10-spec" | 固定值 |
| `--spec-template` | Path | 可选，覆盖默认 SPEC 骨架模板 |

**输出文件**

```
outputs/prompt_<session>_hat10-spec.md
```

**Prompt 结构**

```markdown
# [HARNESS PROBE] System · freeze_id: {freeze_id}

## L0 · 业务拓扑（局部子图）

{mermaid}

## L2 · 冷记忆摘要

{wiki_block}

## L1 · 上一棒信息

- 来源：人/00 提出的需求摘要
- 验收口径：task 中 `## 验收标准`

## 动态任务指令

你正在扮演 10-spec 需求分析帽。严格遵循工作区 `PROMPT_00_draft_spec_or_task_v1_zh.md`：
1. 通读 task 背景、范围、非范围、失败路径。
2. 输出 SPEC 草案，含 §1 背景、§2 范围、§3 行为变更（Delta）、§4 验收标准、§5 失败路径。
3. 默认进行 R0–R5 五轮思考轮，并在 §6 落盘。
4. 不要写实现代码。

【回报硬格式】
Status / Deliverables / Blockers / Judgment（各≤10行）
```

**正确性验证**

```bash
# 1. 文件生成
ls outputs/prompt_*_hat10-spec.md

# 2. 内容检查
python -c "
from pathlib import Path
p = list(Path('outputs').glob('prompt_*_hat10-spec.md'))[-1]
text = p.read_text(encoding='utf-8')
assert '## L0 · 业务拓扑' in text
assert '10-spec' in text
assert 'R0–R5' in text or 'R0-R5' in text
print('10-spec OK')
"
```

---

### 3.2 10-task · task 需求起草帽

**命令**

```bash
python -m src.probe compile \
  --task data/tasks/sample_task.md \
  --entry RAG \
  --hat 10-task \
  --spec data/specs/sample_spec.md
```

**输入**

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `--task` | Path | task.md 路径 |
| `--entry` | str | 入口节点 |
| `--hat` | "10-task" | 固定值 |
| `--spec` | Path | 可选，关联的已 approved SPEC 路径 |

**输出文件**

```
outputs/prompt_<session>_hat10-task.md
```

**Prompt 结构**

与 10-spec 类似，但动态任务指令改为：

```markdown
你正在扮演 10-task 需求分析帽。输入为已 approved SPEC（若提供）+ 本 task 目标：
1. 填充 task §5 思考轮（R0–R5）。
2. 从 SPEC 失败路径/验收标准映射出本 task 的 failure_paths 表。
3. 输出完整 task.md 骨架（Harness 元信息、范围、失败路径、验收标准）。
4. 不要写实现代码。
```

**正确性验证**

```bash
python -c "
from pathlib import Path
p = list(Path('outputs').glob('prompt_*_hat10-task.md'))[-1]
text = p.read_text(encoding='utf-8')
assert '10-task' in text
assert '§5' in text or '失败路径' in text
print('10-task OK')
"
```

---

### 3.3 20-review · task/spec 审核帽

**命令**

```bash
python -m src.probe compile \
  --task data/tasks/sample_task.md \
  --entry RAG \
  --hat 20-review \
  --review-target task
```

**输入**

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `--task` | Path | 待审核的 task.md 或 SPEC.md |
| `--entry` | str | 入口节点 |
| `--hat` | "20-review" | 固定值 |
| `--review-target` | "task" \| "spec" | 审核对象类型 |
| `--previous-round` | Path | 可选，上一版 task/spec 路径，用于 R+1 审核 |

**输出文件**

```
outputs/prompt_<session>_hat20-review.md
```

**Prompt 结构**

```markdown
## 动态任务指令

你正在扮演 20-review 审核帽（{task|spec} 审核）。
1. 通读输入文档全文，重点检查：failure_paths 可操作性、验收标准可验证、范围无隐含扩大、非范围明确。
2. 若通过 → 输出“签收 / 关闭”，更新 human_gate HG-AUDIT-R1 approved。
3. 若阻塞 → 输出“打回至 10-{task|spec}”，列出具体缺口项（≤5 条）。
4. 生成“下一棒可复制 Prompt”。

【回报硬格式】
Status / Deliverables / Blockers / Judgment
- Status: approved / blocked
- Blockers: 若 blocked，逐条列出
- 下一棒: 可直接粘贴的 Prompt 片段
```

**正确性验证**

```bash
python -c "
from pathlib import Path
p = list(Path('outputs').glob('prompt_*_hat20-review.md'))[-1]
text = p.read_text(encoding='utf-8')
assert '20-review' in text
assert 'HG-AUDIT-R1' in text
assert 'approved / blocked' in text
print('20-review OK')
"
```

---

### 3.4 50-reinspect · 独立复检/全局验收帽

**命令**

```bash
python -m src.probe compile \
  --task data/tasks/sample_task.md \
  --entry RAG \
  --hat 50-reinspect \
  --mode independent
```

**输入**

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `--task` | Path | task.md |
| `--entry` | str | 入口节点 |
| `--hat` | "50-reinspect" | 固定值 |
| `--mode` | "independent" \| "global" | 独立复检 vs 全局验收 |
| `--run-output` | Path | 可选，关联的 `task_run_<session>.json` |

**输出文件**

```
outputs/prompt_<session>_hat50-reinspect.md
```

**Prompt 结构**

```markdown
## 动态任务指令

你正在扮演 50-reinspect 独立复检帽（mode={mode}）。
1. 读取 task 全文 + 关联 task_run JSON（若提供）。
2. 核对每个 failure_path_ref 是否有 evidence（命令/文件:行）。
3. 若全部 pass → 输出“CLOSE”，更新 task 状态为 done。
4. 若有 fail → 输出打回目标（30 / 40 / 10-task / 10-spec），不进入合并。
5. 全局验收模式额外检查：freeze_id、graph_delta、human_gate 全 approved。

【回报硬格式】
Status / Deliverables / Blockers / Judgment
- 验收表：| ref | pass/fail | evidence |
- 合并建议：若 global 模式通过，输出 merge 建议
```

**正确性验证**

```bash
python -c "
from pathlib import Path
p = list(Path('outputs').glob('prompt_*_hat50-reinspect.md'))[-1]
text = p.read_text(encoding='utf-8')
assert '50-reinspect' in text
assert 'failure_path_ref' in text
assert 'freeze_id' in text
print('50-reinspect OK')
"
```

---

## 4. `--run` 模拟执行模式

**命令**

```bash
python -m src.probe run \
  --task data/tasks/sample_task.md \
  --entry RAG \
  --from-hat 30 \
  --to-hat 40
```

**输入**

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `--task` | Path | task.md |
| `--entry` | str | 入口节点 |
| `--from-hat` | str | 起始帽子，如 30 |
| `--to-hat` | str | 结束帽子，如 40 |
| `--mock-llm` | bool | 是否使用 Mock LLM（默认 true） |
| `--resume` | Path | 可选，从已有 task_run JSON 恢复 |

**输出**

```
outputs/task_run_<session>.json
```

**task_run.json 结构示例**

```json
{
  "session_id": "abc123",
  "task_path": "data/tasks/sample_task.md",
  "l0_freeze_id": "HARNESS-PROBE-SAMPLE-V0.2",
  "entry_node": "RAG",
  "status": "done",
  "nodes": [
    {
      "id": "30",
      "hat": "30",
      "status": "done",
      "contract_refs": ["F1", "F2", "F3"],
      "evidence": "{\"F1\": \"pass\", ...}",
      "error": null
    },
    {
      "id": "40",
      "hat": "40",
      "status": "done",
      "contract_refs": ["F1", "F2", "F3"],
      "evidence": "{\"F1\": \"pass\", ...}",
      "error": null
    }
  ]
}
```

**正确性验证**

```bash
python -m src.probe run --task data/tasks/sample_task.md --from-hat 30 --to-hat 40 --mock-llm
python -c "
import json
from pathlib import Path
p = sorted(Path('outputs').glob('task_run_*.json'))[-1]
data = json.loads(p.read_text(encoding='utf-8'))
assert data['status'] == 'done'
assert any(n['hat'] == '30' and n['status'] == 'done' for n in data['nodes'])
assert any(n['hat'] == '40' and n['status'] == 'done' for n in data['nodes'])
print('run OK')
"
```

---

## 5. `--watch` freeze_id 漂移检测

**命令**

```bash
python -m src.probe watch \
  --graph data/graph/sample_graph_v2.json \
  --task data/tasks/sample_task.md \
  --interval 5
```

**输入**

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `--graph` | Path | graph.json 路径 |
| `--task` | Path | task.md（含 `**freeze_id**`） |
| `--interval` | int | 轮询秒数，默认 5 |
| `--once` | bool | 只检测一次，不持续轮询 |

**输出**

控制台输出：

```text
Current freeze_id: HARNESS-PROBE-SAMPLE-V0.2
Monitoring data/graph/sample_graph_v2.json (interval=5s)...

⚠️ freeze_id drift detected!
  graph:   HARNESS-PROBE-SAMPLE-V0.3
  task:    HARNESS-PROBE-SAMPLE-V0.2
  impact:  [RAG, FTS, HIT0]
  action:  run `harness verify --impact RAG`
```

**正确性验证**

```bash
# 构造漂移场景
cp data/graph/sample_graph_v2.json /tmp/graph_v0.1.json
cp data/graph/sample_graph_v2.json /tmp/graph_v0.2.json
# 修改 v0.2 的 freeze_id
python -c "
import json
p = Path('/tmp/graph_v0.2.json')
data = json.loads(p.read_text())
data['freeze_id'] = 'V0.2'
p.write_text(json.dumps(data))
"

# 运行一次检测
python -m src.probe watch --graph /tmp/graph_v0.2.json --task data/tasks/sample_task.md --once
```

---

## 6. 代码改动清单

| 文件 | 改动 |
| --- | --- |
| `src/probe.py` | 新增 `--hat`、`--review-target`、`--mode`、`--from-hat`、`--to-hat`、`--watch`、`--interval`、`--once` 参数；新增 `cmd_watch` |
| `src/builder.py` | 新增 `build_hat_prompt(hat, ...)` 分发函数；为 10-spec/10-task/20-review/50-reinspect 生成对应 dynamic_suffix |
| `src/orchestrator.py` | 新增 `run_hat_sequence(from_hat, to_hat)`；支持 `--resume` |
| `src/models.py` | 新增 `RunNodeStatus.drift`、`TaskRunGraph.find_node` 等辅助方法 |
| `src/compiler.py` | 保持现有 contract / human_gate 解析；可能被 SDK 重构替代 |
| `tests/test_probe.py` | 新增 4 顶新帽子的生成测试 + run/watch 测试 |

---

## 7. 验收标准（Phase 1 关闭条件）

- [ ] `compile --hat 10-spec/10-task/20-review/50-reinspect` 各生成合法 Prompt 文件
- [ ] 每顶新帽子的 Prompt 包含该帽专属动态指令
- [ ] `run --from-hat 30 --to-hat 40` 生成完整 `task_run.json` 且 status=done
- [ ] `watch --once` 能检测 freeze_id 漂移并输出影响节点
- [ ] `pytest tests/ -q` 新增用例全部通过，核心函数覆盖率 ≥ 80%

---

## 8. 风险与对策

| 风险 | 对策 |
| --- | --- |
| 新增帽子 Prompt 模板与 workspace PROMPT 不同步 | 每个 hat builder 顶部注释写明对齐的 workspace PROMPT 文件路径 |
| `--run` Mock LLM 输出不稳定 | 固定 seed / deterministic mock；evidence 只记录 contract.verify 字面量 |
| `--watch` 文件系统事件跨平台差异 | 先用轮询（`--interval`），后续可选 `watchdog` |

---

## 给 Cursor

`Harness Probe`、Phase 1、10-spec、10-task、20-review、50-reinspect、`--run`、`--watch`、freeze_id drift
