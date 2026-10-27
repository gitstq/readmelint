"""Minimal, dependency-free Markdown parser.

Builds a structured :class:`Doc` model from a Markdown string so that the
quality rules can reason about headings, code blocks, images, badges, links,
emoji usage and placeholder text without pulling in any third-party library.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #
@dataclass
class CodeBlock:
    lang: str
    content: str


@dataclass
class Image:
    alt: str
    url: str
    is_badge: bool


@dataclass
class Link:
    text: str
    url: str
    is_internal: bool


@dataclass
class Heading:
    level: int
    text: str
    anchor: str


@dataclass
class Doc:
    raw: str = ""
    headings: List[Heading] = field(default_factory=list)
    code_blocks: List[CodeBlock] = field(default_factory=list)
    images: List[Image] = field(default_factory=list)
    links: List[Link] = field(default_factory=list)
    paragraphs: List[str] = field(default_factory=list)
    plain_text: str = ""
    word_count: int = 0
    cjk_count: int = 0
    emoji_count: int = 0
    placeholder_hits: List[str] = field(default_factory=list)
    anchors: List[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
_BADGE_HOSTS = (
    "shields.io",
    "badgen.net",
    "img.shields.io",
    "forthebadge.com",
    "travis-ci",
    "circleci.com",
    "codecov.io",
    "badge.fury.io",
    "github.com/actions",
)

_PLACEHOLDER_PATTERNS = [
    (re.compile(r"\b(TODO|FIXME|TBD|WIP)\b", re.IGNORECASE), "TODO/FIXME 占位符"),
    (re.compile(r"lorem\s+ipsum", re.IGNORECASE), "Lorem ipsum 占位文本"),
    (re.compile(r"your[- ]?(text|code|token|key|password|api[- ]?key)[- ]?here", re.IGNORECASE), "your-*-here 占位符"),
    (re.compile(r"(coming[- ]?soon|placeholder|待补充|待完善|待填写|占位)", re.IGNORECASE), "待补充/占位符"),
    (re.compile(r"example\.com", re.IGNORECASE), "example.com 示例域名"),
]

_EMOJI_RANGES = [
    (0x1F300, 0x1FAFF),
    (0x2600, 0x27BF),
    (0x1F000, 0x1F2FF),
    (0x1F1E6, 0x1F1FF),
    (0x2190, 0x21FF),
    (0x2300, 0x23FF),
    (0x2B00, 0x2BFF),
    (0xFE0F, 0xFE0F),
    (0x2700, 0x27BF),
    (0x1F900, 0x1F9FF),
]


def is_emoji(ch: str) -> bool:
    cp = ord(ch)
    for lo, hi in _EMOJI_RANGES:
        if lo <= cp <= hi:
            return True
    return False


def slugify(text: str) -> str:
    """Approximate GitHub-style heading anchors (enough for link validation)."""
    text = text.strip().lower()
    text = re.sub(r"[`*_~]", "", text)
    # keep unicode word chars, spaces and hyphens; drop the rest
    text = re.sub(r"[^\w\u4e00-\u9fff\s-]", "", text, flags=re.UNICODE)
    text = text.strip().replace(" ", "-")
    text = re.sub(r"-{2,}", "-", text)
    return text


def is_badge_like(alt: str, url: str) -> bool:
    low = url.lower()
    if any(h in low for h in _BADGE_HOSTS):
        return True
    # short alt + image extension == likely a status/version badge
    if re.match(r"^(build|license|version|coverage|status|docs|pyversions|python)$", alt.strip().lower()) and \
       re.search(r"\.(svg|png|jpg|jpeg|gif)$", low):
        return True
    return False


def count_words(text: str) -> tuple[int, int]:
    """Return (word_count, cjk_char_count).

    ASCII words are split on whitespace; each CJK character is counted as one
    "word" so that Chinese READMEs are scored fairly against English ones.
    """
    words = 0
    cjk = 0
    for ch in text:
        if "\u4e00" <= ch <= "\u9fff" or "\u3040" <= ch <= "\u30ff":
            cjk += 1
        elif ch.isspace():
            continue
    # ASCII / latin words
    words = len(re.findall(r"[A-Za-z0-9]+", text))
    return words, cjk


def strip_md(line: str) -> str:
    """Best-effort removal of Markdown syntax to recover plain prose."""
    line = re.sub(r"`([^`]*)`", r"\1", line)            # inline code
    line = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", line)    # images
    line = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", line)  # links -> keep text
    line = re.sub(r"[#>*_~`-]", "", line)               # misc markers
    line = re.sub(r"\s+", " ", line).strip()
    return line


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #
def parse(text: str) -> Doc:
    doc = Doc(raw=text)
    lines = text.split("\n")

    in_fence = False
    fence_marker = ""
    code_buf: List[str] = []
    code_lang = ""
    buf_para: List[str] = []
    plain_parts: List[str] = []

    def flush_para() -> None:
        if buf_para:
            para = " ".join(buf_para).strip()
            if para:
                doc.paragraphs.append(para)
                plain_parts.append(para)
            buf_para.clear()

    for line in lines:
        fm = re.match(r"^(\s*)(```|~~~)(.*)$", line)
        if fm:
            if not in_fence:
                in_fence = True
                fence_marker = fm.group(2)
                code_lang = fm.group(3).strip()
                code_buf = []
            else:
                if fm.group(2) == fence_marker:
                    in_fence = False
                    doc.code_blocks.append(CodeBlock(code_lang, "\n".join(code_buf)))
                else:
                    code_buf.append(line)
            continue

        if in_fence:
            code_buf.append(line)
            continue

        hm = re.match(r"^(#{1,6})\s+(.*)$", line)
        if hm:
            flush_para()
            level = len(hm.group(1))
            htext = hm.group(2).strip()
            anchor = slugify(htext)
            doc.headings.append(Heading(level, htext, anchor))
            doc.anchors.append(anchor)
            plain_parts.append(htext)
            continue

        # markdown images
        for im in re.finditer(r"!\[([^\]]*)\]\(([^)]+)\)", line):
            alt, url = im.group(1), im.group(2).strip()
            doc.images.append(Image(alt, url, is_badge_like(alt, url)))

        # HTML <img> tags (e.g. centered badge rows, demo images)
        for im in re.finditer(r"<img\b[^>]*?>", line):
            tag = im.group(0)
            src_m = re.search(r'src=["\']([^"\']+)["\']', tag)
            if src_m:
                alt_m = re.search(r'alt=["\']([^"\']*)["\']', tag)
                alt = alt_m.group(1) if alt_m else ""
                url = src_m.group(1).strip()
                doc.images.append(Image(alt, url, is_badge_like(alt, url)))

        # links (not images)
        for lm in re.finditer(r"(?<!\!)\[([^\]]*)\]\(([^)]+)\)", line):
            ltext, url = lm.group(1), lm.group(2).strip()
            is_internal = url.startswith("#") or url.startswith("mailto:")
            doc.links.append(Link(ltext, url, is_internal))

        if line.strip() == "":
            flush_para()
        else:
            buf_para.append(strip_md(line))

    flush_para()
    doc.plain_text = "\n".join(plain_parts)

    words, cjk = count_words(doc.plain_text)
    doc.word_count = words
    doc.cjk_count = cjk

    doc.emoji_count = sum(1 for ch in doc.plain_text if is_emoji(ch))

    for pat, label in _PLACEHOLDER_PATTERNS:
        if pat.search(doc.plain_text):
            doc.placeholder_hits.append(label)

    return doc


def detect_language(doc: Doc) -> str:
    """Heuristic zh / en detection based on CJK ratio."""
    total = doc.cjk_count + doc.word_count
    if total == 0:
        return "en"
    return "zh" if doc.cjk_count / total > 0.25 else "en"
