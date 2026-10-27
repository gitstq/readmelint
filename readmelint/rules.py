"""Quality rules for README documentation.

Each rule inspects a parsed :class:`~readmelint.md.Doc` and returns whether it
passed. Rules carry a ``severity`` (blocker / warning / info) and a ``weight``
that feeds the overall score. The registry is fully data-driven so users can
enable / disable / re-weight rules through a JSON config file.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List

from .md import Doc, detect_language


@dataclass
class RuleResult:
    rule_id: str
    name: str
    severity: str
    weight: int
    passed: bool
    message: str
    suggestion: str


@dataclass
class Rule:
    rule_id: str
    name: str
    severity: str
    weight: int
    description: str
    suggestion: str
    check: Callable[[Doc, Dict], bool]


# --------------------------------------------------------------------------- #
# Section keyword maps (language aware)
# --------------------------------------------------------------------------- #
_SECTIONS = {
    "installation": ["install", "安装", "安裝", "setup", "环境", "環境", "environment"],
    "usage": ["usage", "使用", "用法", "quick start", "快速开始", "快速上手", "getting started"],
    "api_config": ["api", "配置", "設定", "configuration", "options", "参数", "參數", "环境变量", "環境變數"],
    "contributing": ["contributing", "贡献", "貢獻", "contribute"],
    "license": ["license", "许可", "許可", "licence", "版权", "版權"],
    "toc": ["table of contents", "目录", "目錄", "contents", "toc"],
    "changelog": ["changelog", "更新日志", "更新日誌", "release notes", "版本", "變更", "变更"],
    "acknowledgements": ["acknowledg", "致谢", "致謝", "thanks", "roadmap", "路线图", "路線圖", "plan"],
}


def _has_section(doc: Doc, key: str) -> bool:
    kws = _SECTIONS[key]
    for h in doc.headings:
        low = h.text.lower()
        if any(k in low for k in kws):
            return True
    # TOC may also be a [TOC] marker in the body
    if key == "toc" and "[toc]" in doc.raw.lower():
        return True
    return False


def _has_multi_lang(doc: Doc) -> bool:
    langs = {"english", "中文", "繁體", "繁体", "简体", "简體", "zh", "en", "français", "español", "日本語", "한국어"}
    found = set()
    for h in doc.headings:
        low = h.text.lower().strip()
        for lg in langs:
            if lg in low:
                found.add(lg)
    return len(found) >= 2


# --------------------------------------------------------------------------- #
# Rule checks
# --------------------------------------------------------------------------- #
def _title(doc: Doc, _ctx) -> bool:
    h1 = [h for h in doc.headings if h.level == 1]
    return len(h1) >= 1


def _description(doc: Doc, _ctx) -> bool:
    # a non-trivial paragraph shortly after the title
    for p in doc.paragraphs[:3]:
        if len(p.split()) >= 6 or len(p) >= 20:
            return True
    return False


def _badges(doc: Doc, _ctx) -> bool:
    return any(img.is_badge for img in doc.images)


def _toc(doc: Doc, _ctx) -> bool:
    return _has_section(doc, "toc")


def _installation(doc: Doc, _ctx) -> bool:
    return _has_section(doc, "installation")


def _usage(doc: Doc, _ctx) -> bool:
    return _has_section(doc, "usage")


def _code_example(doc: Doc, _ctx) -> bool:
    return len(doc.code_blocks) >= 1


def _api_config(doc: Doc, _ctx) -> bool:
    return _has_section(doc, "api_config")


def _contributing(doc: Doc, _ctx) -> bool:
    return _has_section(doc, "contributing")


def _license(doc: Doc, _ctx) -> bool:
    return _has_section(doc, "license")


def _ack(doc: Doc, _ctx) -> bool:
    return _has_section(doc, "acknowledgements")


def _min_length(doc: Doc, ctx) -> bool:
    min_words = ctx.get("min_words", 150)
    # count CJK chars + ascii words; treat 1 CJK char ~ 1 word
    return (doc.word_count + doc.cjk_count) >= min_words


def _screenshot(doc: Doc, _ctx) -> bool:
    if any(not img.is_badge for img in doc.images):
        return True
    # demo gif or screenshot keyword in any image alt/url
    for img in doc.images:
        if "demo" in img.alt.lower() or "screenshot" in img.alt.lower() or img.url.lower().endswith(".gif"):
            return True
    return False


def _no_placeholder(doc: Doc, _ctx) -> bool:
    return len(doc.placeholder_hits) == 0


def _heading_hierarchy(doc: Doc, _ctx) -> bool:
    prev = 0
    for h in doc.headings:
        if prev == 0:
            prev = h.level
            continue
        if h.level > prev + 1:
            return False
        prev = h.level
    return True


def _internal_links(doc: Doc, _ctx) -> bool:
    anchors = {a.lower() for a in doc.anchors}
    broken = 0
    for link in doc.links:
        if link.is_internal:
            anchor = link.url.lstrip("#").lower()
            if anchor and anchor not in anchors:
                broken += 1
    return broken == 0


def _lang_switch(doc: Doc, _ctx) -> bool:
    if not _has_multi_lang(doc):
        return True  # only relevant when multiple languages present
    low = doc.raw.lower()
    return any(k in low for k in ["switch", "切换", "切換", "language", "语言", "語言", "translations", "translate"])


def _changelog(doc: Doc, _ctx) -> bool:
    return _has_section(doc, "changelog")


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #
def _build_registry() -> List[Rule]:
    return [
        Rule("title", "一级标题", "blocker", 15, "应存在至少一个 H1 标题作为项目名",
             "在文档顶部添加 `# 项目名称`。", _title),
        Rule("description", "项目描述", "warning", 8, "标题下方应有简短的项目描述",
             "在 H1 之后补充 1-2 句项目定位与核心价值。", _description),
        Rule("badges", "状态徽章", "info", 5, "建议包含构建/版本/协议等状态徽章",
             "在标题下添加 shields.io 徽章（build / license / version）。", _badges),
        Rule("toc", "目录", "info", 5, "长文档建议提供目录方便跳转",
             "在开头添加 `## 目录` 或 `[TOC]`。", _toc),
        Rule("installation", "安装说明", "warning", 12, "必须包含安装步骤",
             "添加 `## 安装 / Installation` 章节与命令。", _installation),
        Rule("usage", "使用说明", "warning", 12, "必须包含基本用法",
             "添加 `## 快速开始 / Quick Start` 章节。", _usage),
        Rule("code_example", "代码示例", "warning", 10, "应至少包含一个代码块示例",
             "在用法章节中加入可复制的代码块。", _code_example),
        Rule("api_config", "配置/API 说明", "info", 5, "建议说明配置项或 API",
             "添加 `## 配置 / Configuration` 章节。", _api_config),
        Rule("contributing", "贡献指南", "info", 5, "建议包含贡献方式",
             "添加 `## 贡献 / Contributing` 章节或链接 CONTRIBUTING。", _contributing),
        Rule("license", "开源协议", "blocker", 12, "必须声明开源协议",
             "添加 `## 许可证 / License` 章节（如 MIT）。", _license),
        Rule("acknowledgements", "致谢/路线图", "info", 3, "建议包含致谢或路线图",
             "添加 `## 路线图 / Roadmap` 或 `## 致谢 / Acknowledgements`。", _ack),
        Rule("min_length", "内容充实度", "warning", 8, "正文应达到一定篇幅",
             "补充更多说明、示例与场景，避免过于单薄。", _min_length),
        Rule("screenshot", "截图/演示", "info", 6, "建议提供截图或演示动图",
             "添加项目截图或 demo gif 增强可读性。", _screenshot),
        Rule("no_placeholder", "无占位符", "warning", 10, "不应残留 TODO/FIXME/占位文本",
             "替换或删除所有占位符与示例占位内容。", _no_placeholder),
        Rule("heading_hierarchy", "标题层级", "warning", 5, "标题层级应连续，不跳级",
             "修正跳级标题（如 H1 后直接 H3）。", _heading_hierarchy),
        Rule("internal_links", "内链有效", "warning", 5, "内部锚点链接应可正确跳转",
             "修正失效的 `#anchor` 内部链接。", _internal_links),
        Rule("lang_switch", "多语言切换", "info", 4, "多语言文档应提供语言切换说明",
             "在顶部说明如何切换语言版本。", _lang_switch),
        Rule("changelog", "更新日志", "info", 3, "建议维护更新日志",
             "添加 `## 更新日志 / Changelog` 章节。", _changelog),
    ]


DEFAULT_RULES: List[Rule] = _build_registry()
RULE_IDS = [r.rule_id for r in DEFAULT_RULES]


def apply_rules(doc: Doc, enabled: Dict[str, dict] | None = None) -> List[RuleResult]:
    """Run all rules, honouring an optional enable/weight override map."""
    enabled = enabled or {}
    ctx = {"min_words": enabled.get("__min_words__", 150) if isinstance(enabled.get("__min_words__"), int) else 150}
    results: List[RuleResult] = []
    for rule in DEFAULT_RULES:
        override = enabled.get(rule.rule_id, {})
        if override.get("enabled") is False:
            continue
        weight = int(override.get("weight", rule.weight))
        try:
            passed = bool(rule.check(doc, ctx))
        except Exception:
            passed = False
        results.append(RuleResult(
            rule_id=rule.rule_id,
            name=rule.name,
            severity=rule.severity,
            weight=weight,
            passed=passed,
            message=rule.description,
            suggestion=rule.suggestion,
        ))
    return results


def load_rules_config(path: str) -> Dict:
    """Load a JSON rules override file. Supports per-rule enabled/weight and
    a top-level ``min_words`` setting."""
    import json
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    cfg: Dict = {}
    if "min_words" in data:
        cfg["__min_words__"] = int(data["min_words"])
    for rid in RULE_IDS:
        if rid in data:
            cfg[rid] = data[rid]
    return cfg
