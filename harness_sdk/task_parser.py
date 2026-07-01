"""Harness Task Parser · Markdown 任务单解析。

解析能力：
- YAML frontmatter（可选）
- Harness 元信息表（``| **key** | value |``）
- 人工闸表
- 验收标准 ``- [ ]`` / ``- [x]`` 列表
- 失败路径表
- 正文分节

本模块保持无 CLI 副作用，只返回结构化数据或抛出 ``pydantic.ValidationError``。
"""

from __future__ import annotations

import re
import warnings
from pathlib import Path
from typing import Any

import yaml

from harness_sdk.task_schema import (
    AcceptanceItem,
    FailurePath,
    HumanGate,
    TaskInfo,
    TaskSchema,
)


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_META_ROW_RE = re.compile(
    r"^\|\s*\*\*(?P<key>[^|*]+)\*\*\s*\|\s*(?P<val>[^|]*)\|\s*$",
    re.MULTILINE,
)
_HUMAN_GATE_HEADER_RE = re.compile(
    r"^\|\s*human_gate_id\s*\|\s*status\s*\|\s*blocks_hats\s*\|",
    re.IGNORECASE | re.MULTILINE,
)
_ACCEPTANCE_RE = re.compile(r"^-\s+\[([xX ])\]\s+(.*)$", re.MULTILINE)


def split_frontmatter(text: str) -> tuple[dict[str, Any] | None, str]:
    """切分 YAML frontmatter 与正文。

    返回 ``(frontmatter_dict, body)``；若无 frontmatter 则返回 ``(None, text)``。
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return None, text
    try:
        data = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML frontmatter: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("YAML frontmatter must be a mapping")
    return data, text[match.end() :]


def _section_body(text: str, keyword: str) -> str:
    """截取 ``##`` 或 ``###`` 标题中含 keyword 的节区，到同级或更高层级标题为止。"""
    heading_re = re.compile(r"^(#{2,3})\s+([^\n]+)$", re.MULTILINE)
    for match in heading_re.finditer(text):
        title = match.group(2).strip()
        if keyword in title:
            level = len(match.group(1))
            start = match.end()
            for next_match in heading_re.finditer(text, pos=start):
                if len(next_match.group(1)) <= level:
                    return text[start:next_match.start()]
            return text[start:]
    return ""


def _table_rows(section_text: str) -> list[list[str]]:
    """从节区文本中提取 markdown 表格数据行（跳过表头与分隔线）。"""
    rows: list[list[str]] = []
    for line in section_text.splitlines():
        line = line.strip()
        if not line.startswith("|") or not line.endswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not cells:
            continue
        if all(set(cell) <= {"-", ":", " "} for cell in cells):
            continue
        rows.append(cells)
    return rows


def _strip_inline_code(value: str) -> str:
    return value.strip().strip("`").strip()


def _header_indices(header: list[str], *keywords: str) -> dict[str, int]:
    """根据关键词在表头中的位置返回列名 -> 索引。"""
    indices: dict[str, int] = {}
    for idx, cell in enumerate(header):
        cleaned = cell.strip()
        for kw in keywords:
            if kw in cleaned:
                indices[kw] = idx
                break
    return indices


def parse_meta_table(text: str) -> dict[str, str]:
    """解析 Harness 元信息表（通常在 ``## Harness 元信息`` 之前）。"""
    fields: dict[str, str] = {}
    for match in _META_ROW_RE.finditer(text):
        key = match.group("key").strip()
        val = _strip_inline_code(match.group("val"))
        fields[key] = val
    return fields


def parse_human_gates(text: str) -> list[HumanGate]:
    """解析 ``人工闸`` 表格。"""
    body = _section_body(text, "人工闸")
    if not body or not _HUMAN_GATE_HEADER_RE.search(body):
        return []
    rows = _table_rows(body)
    if not rows:
        return []

    header = [cell.strip() for cell in rows[0]]
    idx = _header_indices(header, "human_gate_id", "status", "blocks_hats")
    if "human_gate_id" not in idx or "status" not in idx:
        return []

    gates: list[HumanGate] = []
    gate_id_re = re.compile(r"^HG-[A-Z0-9-]+$")
    for row in rows[1:]:
        if len(row) < 2:
            continue
        gate_id = _strip_inline_code(row[idx.get("human_gate_id", 0)])
        if not gate_id_re.match(gate_id):
            continue
        status = _strip_inline_code(row[idx.get("status", 1)])
        blocks_text = row[idx.get("blocks_hats", 2)] if "blocks_hats" in idx else ""
        description = ""
        if len(row) > max(idx.values()) + 1:
            description = _strip_inline_code(row[max(idx.values()) + 1])
        gates.append(
            HumanGate(
                gate_id=gate_id,
                status=status,  # type: ignore[arg-type]
                blocks_hats=blocks_text,  # type: ignore[arg-type]
                description=description,
            )
        )
    return gates


def parse_failure_paths(text: str) -> list[FailurePath]:
    """解析 ``失败路径`` 表格。"""
    body = _section_body(text, "失败路径")
    rows = _table_rows(body)
    if not rows:
        return []

    header = [cell.strip() for cell in rows[0]]
    idx = _header_indices(
        header, "触发条件", "系统行为", "是否可重试", "用户可见类型"
    )
    if "触发条件" not in idx or "系统行为" not in idx:
        return []

    paths: list[FailurePath] = []
    for row in rows[1:]:
        if len(row) < 2:
            continue
        trigger = _strip_inline_code(row[idx["触发条件"]])
        if trigger in ("触发条件", "---", "--"):
            continue
        behavior = _strip_inline_code(row[idx.get("系统行为", 1)])
        retry = row[idx.get("是否可重试", 2)] if "是否可重试" in idx else ""
        visible = (
            _strip_inline_code(row[idx.get("用户可见类型", 3)])
            if "用户可见类型" in idx
            else ""
        )
        paths.append(
            FailurePath(
                trigger=trigger,
                behavior=behavior,
                retry=retry,
                visible_type=visible,
            )
        )
    return paths


def parse_acceptance_items(text: str) -> list[AcceptanceItem]:
    """解析 ``验收标准`` 中的 ``- [ ]`` / ``- [x]`` 列表。"""
    body = _section_body(text, "验收标准")
    items: list[AcceptanceItem] = []
    for match in _ACCEPTANCE_RE.finditer(body):
        checked = match.group(1).lower() == "x"
        text_value = match.group(2).strip()
        items.append(AcceptanceItem(text=text_value, checked=checked))
    return items


def parse_sections(text: str) -> dict[str, str]:
    """按 ``##`` 顶级标题切分正文，返回 ``标题 -> 节区体``。"""
    sections: dict[str, str] = {}
    pattern = re.compile(r"^##\s+(.+?)\s*\n(.*?)(?=^##\s|\Z)", re.MULTILINE | re.DOTALL)
    for match in pattern.finditer(text):
        title = match.group(1).strip()
        sections[title] = match.group(2).strip()
    return sections


def _freeze_id_warning(filename: str, freeze_id: str | None) -> str | None:
    """检查文件名中的版本号与 freeze_id 是否一致，返回警告文本或 None。"""
    if not freeze_id:
        return None
    import re as _re

    file_match = _re.search(r"v\d+(_\d+)+", filename)
    freeze_match = _re.search(r"v\d+(\.\d+)+", freeze_id)
    if not file_match or not freeze_match:
        return None
    file_version = file_match.group().replace("_", ".")
    freeze_version = freeze_match.group()
    if file_version != freeze_version:
        return (
            f"freeze_id '{freeze_id}' may not match filename version "
            f"'{file_match.group()}'"
        )
    return None


def parse_task_text(
    text: str,
    *,
    path: Path | None = None,
    repo_root: Path | None = None,
) -> tuple[TaskSchema, list[str]]:
    """从 Markdown 文本解析任务单。

    返回 ``(task_schema, warnings)``。解析成功但字段校验失败时抛出
    ``pydantic.ValidationError``。
    """
    parsed_warnings: list[str] = []

    frontmatter, body = split_frontmatter(text)
    if frontmatter is None:
        frontmatter = {}

    # 1. 元信息：frontmatter 优先；若存在 metadata 子键则用之，否则把整个 frontmatter 当作元信息
    if "metadata" in frontmatter:
        meta: dict[str, Any] = dict(frontmatter.get("metadata", {}) or {})
    else:
        meta = dict(frontmatter)
    table_meta = parse_meta_table(text)
    for key, value in table_meta.items():
        if key not in meta:
            meta[key] = value

    # 2. 结构化内容
    human_gates = list(frontmatter.get("human_gates", [])) or parse_human_gates(text)
    acceptance = list(frontmatter.get("acceptance", [])) or parse_acceptance_items(text)
    failure_paths = (
        list(frontmatter.get("failure_paths", [])) or parse_failure_paths(text)
    )
    sections = parse_sections(body)

    # 3. 组装 TaskInfo
    info = TaskInfo(
        title=meta.get("title", ""),
        track=meta.get("track", ""),
        lightweight_task=meta.get("lightweight_task", ""),
        module_id=meta.get("module_id", ""),
        graph_delta=meta.get("graph_delta") or None,
        freeze_id=meta.get("freeze_id") or None,
        test_strategy=meta.get("test_strategy"),
        human_gates=human_gates,
        acceptance=acceptance,
        failure_paths=failure_paths,
        background=sections.get("背景与目标", ""),
        scope=sections.get("范围", ""),
        implementation_notes=sections.get("实现备忘", ""),
    )

    # 4. freeze_id 一致性警告（非错误）
    filename = path.name if path else ""
    freeze_warning = _freeze_id_warning(filename, info.freeze_id)
    if freeze_warning:
        parsed_warnings.append(freeze_warning)
        warnings.warn(freeze_warning, UserWarning, stacklevel=2)

    # 5. graph_delta 存在性校验通过 TaskSchema 模型触发
    schema = TaskSchema(metadata=info, content=sections)
    return schema, parsed_warnings


def parse_task_file(
    path: str | Path,
    *,
    repo_root: Path | None = None,
) -> tuple[TaskSchema, list[str]]:
    """从文件路径解析任务单。"""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    return parse_task_text(text, path=p, repo_root=repo_root)
