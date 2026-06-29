#!/usr/bin/env python3
"""Harness task 文件机械校验（harness-probe 定制版 · 含 IMP-09 human_gate 校验）。

规则真值：本仓 AGENTS.md · docs/harness/prompts/FRAGMENT_30_gate_verify_v1_zh.md
上游：ai-ink-brain-api-python/tools/harness_task_validate.py（PR #225）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ACTIVE_TASKS = REPO_ROOT / "docs" / "harness" / "tasks" / "active"

META_FIELD = re.compile(
    r"^\|\s*\*\*(?P<key>[^|*]+)\*\*\s*\|\s*(?P<val>[^|]*)\|\s*$",
    re.M,
)
SECTION = re.compile(r"^## (?P<title>.+)$", re.M)
HUMAN_GATE_HEADER = re.compile(
    r"^\|\s*human_gate_id\s*\|\s*status\s*\|\s*blocks_hats\s*\|",
    re.I | re.M,
)


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str  # error | warn
    message: str


@dataclass
class ValidationResult:
    path: Path
    findings: list[Finding]

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "error"]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "warn"]

    @property
    def ok(self) -> bool:
        return not self.errors


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _meta_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for m in META_FIELD.finditer(text):
        key = m.group("key").strip()
        val = m.group("val").strip().strip("`")
        fields[key] = val
    return fields


def _section_body(text: str, title: str) -> str:
    headings = list(SECTION.finditer(text))
    for i, m in enumerate(headings):
        if title not in m.group("title").strip():
            continue
        start = m.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        return text[start:end]
    return ""


def _table_rows(section_text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in section_text.splitlines():
        line = line.strip()
        if not line.startswith("|") or line.endswith("|") is False:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not cells:
            continue
        if all(set(c) <= {"-", " ", ":"} for c in cells):
            continue
        rows.append(cells)
    return rows


def _touches_api(text: str) -> bool:
    for title in ("范围", "实现备忘", "依赖与引用", "行为变更"):
        body = _section_body(text, title)
        if "api/" in body:
            return True
    return False


def _delta_body(text: str) -> str:
    for title in ("行为变更（Delta · 可选）", "行为变更（Delta）", "行为变更"):
        body = _section_body(text, title)
        if body.strip():
            return body
    return ""


def _failure_path_rows(text: str) -> list[list[str]]:
    body = _section_body(text, "失败路径")
    rows = _table_rows(body)
    if not rows:
        return []
    header = rows[0]
    data: list[list[str]] = []
    for row in rows[1:]:
        if row[0].startswith("#") or row[0] in {"#", "F#"}:
            continue
        if row[0].startswith("F") or row[0].isdigit():
            data.append(row)
        elif len(row) >= 3 and row[0] and row[0] not in header:
            data.append(row)
    return data


def _acceptance_body(text: str) -> str:
    return _section_body(text, "验收标准")


def validate_task_text(text: str, path: Path | None = None) -> ValidationResult:
    rel = str(path) if path else "<text>"
    findings: list[Finding] = []
    meta = _meta_fields(text)

    if not meta.get("test_strategy"):
        findings.append(
            Finding(
                "HARNESS-META-MISSING",
                "error",
                f"{rel}: 缺少 Harness 元信息表 test_strategy",
            )
        )
        return ValidationResult(path=path or Path(rel), findings=findings)

    test_strategy = meta.get("test_strategy", "").strip().lower()
    note = meta.get("test_strategy_note", "").strip()
    semi_auto = meta.get("semi_auto", "").strip().lower() == "true"
    git_branch = meta.get("git_branch", "").strip()

    if test_strategy == "not_applicable" and not note:
        findings.append(
            Finding(
                "TEST-STRATEGY-NOTE-MISSING",
                "error",
                f"{rel}: not_applicable 须填写 test_strategy_note",
            )
        )

    fp_rows = _failure_path_rows(text)
    if not fp_rows:
        findings.append(
            Finding(
                "FAILURE-PATHS-EMPTY",
                "error",
                f"{rel}: failure_paths 表至少 1 行数据",
            )
        )

    acceptance = _acceptance_body(text).lower()
    if test_strategy == "required" and "pytest" not in acceptance:
        findings.append(
            Finding(
                "TEST-STRATEGY-REQUIRED-PYTEST",
                "error",
                f"{rel}: test_strategy=required 时验收须含 pytest 表述",
            )
        )

    if _touches_api(text) and test_strategy == "not_applicable":
        findings.append(
            Finding(
                "API-NOT-APPLICABLE",
                "error",
                f"{rel}: 触达 api/ 时禁止 test_strategy=not_applicable",
            )
        )

    delta = _delta_body(text)
    if delta:
        has_delta_heading = bool(
            re.search(r"^###\s+(ADDED|MODIFIED|REMOVED)\b", delta, re.M | re.I)
        )
        explicit_none = re.search(r"^\s*无\s*$", delta.strip(), re.M) is not None
        if not has_delta_heading and not explicit_none:
            findings.append(
                Finding(
                    "DELTA-SECTION-MISSING",
                    "warn",
                    f"{rel}: §行为变更须含 ADDED/MODIFIED/REMOVED 或显式「无」",
                )
            )
        if _touches_api(text) and explicit_none and not has_delta_heading:
            findings.append(
                Finding(
                    "DELTA-API-ONLY-NONE",
                    "warn",
                    f"{rel}: 触达 api/ 时 Delta 不宜仅写「无」",
                )
            )
    elif _touches_api(text):
        findings.append(
            Finding(
                "DELTA-SECTION-MISSING",
                "warn",
                f"{rel}: 触达 api/ 建议填写 §行为变更 Delta",
            )
        )

    if fp_rows:
        for row in fp_rows:
            scenario = row[1] if len(row) > 1 else ""
            if not scenario or scenario in {"Scenario ID", "—", "-"}:
                findings.append(
                    Finding(
                        "SCENARIO-ID-MISSING",
                        "warn",
                        f"{rel}: failure_paths 行缺少 Scenario ID",
                    )
                )
                break

    if semi_auto and git_branch in {"main", "production", ""}:
        findings.append(
            Finding(
                "GIT-BRANCH-MAIN",
                "error",
                f"{rel}: semi_auto=true 时 git_branch 须为非 main 任务分支",
            )
        )

    if "human_gate_id" in text or "### 人工闸" in text:
        if not HUMAN_GATE_HEADER.search(text):
            findings.append(
                Finding(
                    "HUMAN-GATE-FORMAT",
                    "error",
                    f"{rel}: human_gate 表须含 human_gate_id | status | blocks_hats 列",
                )
            )

    return ValidationResult(path=path or Path(rel), findings=findings)


def validate_file(path: Path) -> ValidationResult:
    return validate_task_text(_read(path), path)


def iter_active_tasks() -> list[Path]:
    if not ACTIVE_TASKS.is_dir():
        return []
    out: list[Path] = []
    for p in sorted(ACTIVE_TASKS.glob("*.md")):
        if "_AGENT_PROMPT" in p.name:
            continue
        out.append(p)
    return out


def format_text(result: ValidationResult) -> str:
    rel = result.path
    if rel.is_absolute():
        try:
            rel = rel.relative_to(REPO_ROOT)
        except ValueError:
            pass
    lines = [f"=== {rel} ==="]
    if result.ok and not result.warnings:
        lines.append("OK")
        return "\n".join(lines)
    for f in result.findings:
        lines.append(f"[{f.severity.upper()}] {f.rule_id}: {f.message}")
    lines.append("FAIL" if result.errors else "OK (warnings)")
    return "\n".join(lines)


def format_json(results: list[ValidationResult]) -> str:
    payload = []
    for r in results:
        rel = r.path
        if rel.is_absolute():
            try:
                rel = rel.relative_to(REPO_ROOT)
            except ValueError:
                pass
        payload.append(
            {
                "path": str(rel),
                "ok": r.ok,
                "errors": [asdict(f) for f in r.errors],
                "warnings": [asdict(f) for f in r.warnings],
            }
        )
    return json.dumps(payload, ensure_ascii=False, indent=2)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Harness task 文件校验")
    parser.add_argument(
        "paths",
        nargs="*",
        help="task 文件路径（默认 stdin 无则须 --all-active）",
    )
    parser.add_argument(
        "--all-active",
        action="store_true",
        help="校验 docs/tasks/active 下全部 task（排除 *_AGENT_PROMPT）",
    )
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args(argv)

    task_paths: list[Path] = []
    if args.all_active:
        task_paths = iter_active_tasks()
    elif args.paths:
        task_paths = [
            (REPO_ROOT / p).resolve() if not Path(p).is_absolute() else Path(p)
            for p in args.paths
        ]
    else:
        parser.error("specify task path(s) or --all-active")

    results: list[ValidationResult] = []
    for tp in task_paths:
        if not tp.is_file():
            print(f"harness_task_validate: file not found: {tp}", file=sys.stderr)
            return 1
        results.append(validate_file(tp))

    if args.json:
        print(format_json(results))
    else:
        for r in results:
            print(format_text(r))
            if len(results) > 1:
                print()

    if any(not r.ok for r in results):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
