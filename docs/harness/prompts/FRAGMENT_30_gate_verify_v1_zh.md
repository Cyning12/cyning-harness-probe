# FRAGMENT · 30 开工前 GATE_VERIFY（mandatory · 首输出）

> 嵌入 **30 invoke** 与 `30-execute-code.md`。  
> **禁止**在 invoke 中预写 `HG-AUDIT-R1 approved`；须 **读 task 人工闸表** 填表。

## 首输出形状（未通过则 **零 diff**）

```text
## 人工闸扫描（GATE_VERIFY · 首输出）

| human_gate_id | task表status | 用户/invoke声称 | 一致？ | blocks_30 | 30可开工？ |
|---------------|--------------|-----------------|--------|-----------|------------|
| HG-TASK-DRAFT | {读表} | {若有} | {Y/N} | {Y/N} | … |
| HG-AUDIT-R1 | {读表} | {若有} | {Y/N} | Y | … |
| HG-GRAPH-MODULES | {01_struct或—} | — | — | … | … |

reviews：task_*_audit_R1_*.md 存在且 R1 通过？ {是/否}

冲突规则：task表 pending 且用户/invoke 称 approved → **STOP** · 以 task 表为准

结论：{STOP · 签闸指引 | 可进入读码/改码}

机械辅助（30 改码前必须）：`npx @cyning/harness verify --target <meta> --task docs/tasks/active/task_*.md [--json] [--agent-hint] [--workspace-root <Projects>]`
```

## Agent 纪律

1. **先**输出上表，**再**读源码 / 改 `packages/**`。  
2. 用户「确认…approved」= **须核验**，非已签事实。  
3. task §5「可 30」= **预判**，闸真值 **仅** §人工闸表。
