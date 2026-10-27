"""Report formatters: human readable (ANSI), JSON and Markdown."""

from __future__ import annotations

import json
from typing import List, Optional

from .rules import RuleResult
from .scorer import Score


# ANSI colors (disabled automatically when output is not a TTY / forced plain)
_RESET = "\033[0m"
_BOLD = "\033[1m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_BLUE = "\033[34m"
_CYAN = "\033[36m"

_COLOR_ON = True


def set_color(on: bool) -> None:
    global _COLOR_ON
    _COLOR_ON = on


def _c(code: str, text: str) -> str:
    if not _COLOR_ON:
        return text
    return f"{code}{text}{_RESET}"


_SEV_COLOR = {"blocker": _RED, "warning": _YELLOW, "info": _BLUE}
_SEV_LABEL = {"blocker": "阻断", "warning": "警告", "info": "提示"}


def _mark(passed: bool) -> str:
    return _c(_GREEN, "✓") if passed else _c(_RED, "✗")


def _grade_color(grade: str) -> str:
    return {  # noqa: E731
        "A": _GREEN, "B": _GREEN, "C": _YELLOW, "D": _YELLOW, "F": _RED
    }.get(grade, _RESET)


# --------------------------------------------------------------------------- #
# Text (human) report
# --------------------------------------------------------------------------- #
def to_text(path: str, score: Score, results: List[RuleResult], lang: str) -> str:
    lines = []
    lines.append(_c(_BOLD, f"📋 ReadmeLint 报告 — {path}"))
    lines.append("")
    lines.append(f"  评分: {_c(_grade_color(score.grade), _BOLD + f'{score.value}/100 ({score.grade})')}")
    lines.append(f"  语言: {lang}   通过: {score.passed}   未通过: {score.failed}"
                 f"   阻断未过: {score.blockers_failed}")
    lines.append("")
    lines.append(_c(_BOLD, "  规则明细"))
    lines.append("  " + "-" * 52)
    for r in results:
        col = _SEV_COLOR.get(r.severity, _RESET)
        sev = _c(col, _SEV_LABEL.get(r.severity, r.severity))
        head = f"  {_mark(r.passed)} [{sev}] {r.name}"
        lines.append(head)
        if not r.passed:
            lines.append(f"      · {r.message}")
            lines.append(f"      · 💡 {_c(_CYAN, r.suggestion)}")
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# JSON report
# --------------------------------------------------------------------------- #
def to_json(path: str, score: Score, results: List[RuleResult], lang: str) -> str:
    payload = {
        "path": path,
        "language": lang,
        "score": score.value,
        "grade": score.grade,
        "summary": {
            "passed": score.passed,
            "failed": score.failed,
            "blockers_failed": score.blockers_failed,
            "by_severity": score.by_severity,
        },
        "results": [
            {
                "rule_id": r.rule_id,
                "name": r.name,
                "severity": r.severity,
                "weight": r.weight,
                "passed": r.passed,
                "message": r.message,
                "suggestion": r.suggestion,
            }
            for r in results
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------------- #
# Markdown report
# --------------------------------------------------------------------------- #
_BADGE_COLOR = {"A": "brightgreen", "B": "green", "C": "yellow", "D": "orange", "F": "red"}


def to_markdown(path: str, score: Score, results: List[RuleResult], lang: str) -> str:
    color = _BADGE_COLOR.get(score.grade, "lightgrey")
    out = []
    out.append(f"# 📋 ReadmeLint 检测报告")
    out.append("")
    out.append(f"**文件**: `{path}`  ")
    out.append(f"**语言**: {lang}  ")
    out.append(
        f"![score](https://img.shields.io/badge/quality-{score.value}%2F100-{color})"
        f" ![grade](https://img.shields.io/badge/grade-{score.grade}-{color})"
    )
    out.append("")
    out.append("## 规则明细")
    out.append("")
    out.append("| 状态 | 级别 | 规则 | 说明 |")
    out.append("| --- | --- | --- | --- |")
    for r in results:
        mark = "✅" if r.passed else "❌"
        sev = _SEV_LABEL.get(r.severity, r.severity)
        msg = r.message if r.passed else f"{r.message} —— 💡{r.suggestion}"
        out.append(f"| {mark} | {sev} | {r.name} | {msg} |")
    out.append("")
    out.append(f"> 总分 **{score.value}/100**（等级 {score.grade}），"
               f"通过 {score.passed} 项，未通过 {score.failed} 项，"
               f"其中阻断级未通过 {score.blockers_failed} 项。")
    out.append("")
    return "\n".join(out)


def aggregate_summary(rows: List[dict]) -> str:
    """Pretty aggregate table for batch mode (text)."""
    lines = [_c(_BOLD, "📊 批量检测汇总")]
    lines.append("  " + "-" * 64)
    lines.append(f"  {'路径':<40} {'评分':>6} {'等级':>4}")
    lines.append("  " + "-" * 64)
    for r in rows:
        lines.append(f"  {r['path'][:40]:<40} {r['score']:>6} {r['grade']:>4}")
    avg = round(sum(r["score"] for r in rows) / len(rows)) if rows else 0
    lines.append("  " + "-" * 64)
    lines.append(f"  {'平均':<40} {avg:>6}")
    return "\n".join(lines)
