# Harness invoke 快照模板

> **用途**：每 **新帽** 开局时，将 **占位符已全部替换** 的 §3 Prompt 落盘。  
> **路径**：`docs/harness/invokes/by-task/<task_slug>/invoke_YYYYMMDD_<hat>_<slug>.md`

---

## 元信息表（必填）

| 字段 | 值 |
|------|-----|
| hat_id | 10 / 22 / 30 / 40 / 50 / 00 / CLOSE |
| task_slug | `<slug>` |
| freeze_id | （可选） |
| task_paths | `docs/tasks/active/task_….md` |
| related_review_or_none | `docs/harness/reviews/…` 或 `无` |
| git_branch | `task/<slug>` |
| worktree_root | （并行时必填 · 相对仓根） |
| created_utc_or_local | YYYY-MM-DD |
| notes | （可选） |

---

## 可复制 Prompt 快照

```text
（粘贴本帽 TEMPLATE-*-invoke §3 全文 · 占位符须全部替换）
```

---

## 交付摘要（本帽结束时填）

- **验证命令** + 退出码
- **变更路径** 列表
- **下一棒** slug 或「交还 00」

---

## 纪律

| 规则 | 说明 |
|------|------|
| 同帽追问 | **不** 新增 invoke；沿用本节路径 |
| 打回重开 | 新文件或 `_r2` 后缀 |
| 与 reviews 分工 | reviews = 结论；invoke = **当时指令** |
| commit | 落盘 + task 回填后再 commit（见 HANDOFF） |

---

## 完整库 POINTER

Ink 工作区：`docs/harness/invokes/README.md` · 各 `TEMPLATE-*-invoke.md` §3

## 修订记录

| 日期 | 说明 |
|------|------|
| YYYY-MM-DD | 从 cyning-harness 嵌入 |
