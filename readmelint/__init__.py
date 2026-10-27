"""ReadmeLint — 零依赖的 README 质量评分与检测工具。

A zero-dependency quality linter for README / documentation files. It parses
Markdown with only the standard library, scores the document against a
configurable set of open-source best-practice rules and emits actionable,
human / JSON / Markdown reports.
"""

from __future__ import annotations

__version__ = "1.0.0"

from .md import Doc, parse, detect_language
from .rules import apply_rules, DEFAULT_RULES, RULE_IDS, load_rules_config
from .scorer import score, Score
from .report import to_text, to_json, to_markdown

__all__ = [
    "__version__",
    "Doc", "parse", "detect_language",
    "apply_rules", "DEFAULT_RULES", "RULE_IDS", "load_rules_config",
    "score", "Score",
    "to_text", "to_json", "to_markdown",
]
