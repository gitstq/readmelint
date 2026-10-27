"""Weighted scoring model and grade bands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .rules import RuleResult


@dataclass
class Score:
    value: int
    grade: str
    passed: int
    failed: int
    blockers_failed: int
    warnings_failed: int
    by_severity: dict


_GRADES = [(90, "A"), (75, "B"), (60, "C"), (40, "D"), (0, "F")]


def grade_for(score: int) -> str:
    for threshold, g in _GRADES:
        if score >= threshold:
            return g
    return "F"


def score(results: List[RuleResult]) -> Score:
    total_w = sum(r.weight for r in results) or 1
    passed_w = sum(r.weight for r in results if r.passed)
    value = round(100 * passed_w / total_w)

    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    blockers_failed = sum(1 for r in results if not r.passed and r.severity == "blocker")
    warnings_failed = sum(1 for r in results if not r.passed and r.severity == "warning")

    by_sev = {}
    for r in results:
        d = by_sev.setdefault(r.severity, {"passed": 0, "failed": 0, "total": 0})
        d["total"] += 1
        if r.passed:
            d["passed"] += 1
        else:
            d["failed"] += 1

    return Score(
        value=value,
        grade=grade_for(value),
        passed=passed,
        failed=failed,
        blockers_failed=blockers_failed,
        warnings_failed=warnings_failed,
        by_severity=by_sev,
    )
