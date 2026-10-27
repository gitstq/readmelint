"""Unit tests for ReadmeLint (standard library only)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from readmelint.md import parse, detect_language, slugify
from readmelint.rules import apply_rules, DEFAULT_RULES, RULE_IDS
from readmelint.scorer import score


GOOD_README = """# My Great Project

A lightweight tool that does X and solves Y pain point for developers.

![build](https://img.shields.io/badge/build-passing-green)
![license](https://img.shields.io/badge/license-MIT-blue)

## 目录
- 安装
- 使用

## 安装 / Installation

```bash
pip install my-great-project
```

## 快速开始 / Quick Start

```python
from myproject import run
run()
```

![demo](docs/demo.gif)

## 配置 / Configuration

Set `API_KEY` via environment variable.

## 贡献 / Contributing

PRs are welcome, see CONTRIBUTING.

## 许可证 / License

Released under the MIT License.

## 路线图 / Roadmap

- v2 with plugins
"""


BAD_README = """# x

TODO: write description

## install
soon

## usage
coming soon

See [broken](#nonexistent-anchor) for details.
"""


class TestParser(unittest.TestCase):
    def test_headings(self):
        doc = parse(GOOD_README)
        self.assertTrue(any(h.level == 1 for h in doc.headings))
        self.assertGreaterEqual(len(doc.headings), 6)

    def test_code_blocks(self):
        doc = parse(GOOD_README)
        self.assertGreaterEqual(len(doc.code_blocks), 2)
        langs = {c.lang for c in doc.code_blocks}
        self.assertIn("bash", langs)

    def test_badge_detection(self):
        doc = parse(GOOD_README)
        self.assertTrue(any(img.is_badge for img in doc.images))

    def test_non_badge_image(self):
        doc = parse(GOOD_README)
        self.assertTrue(any(not img.is_badge for img in doc.images))

    def test_placeholder_detection(self):
        doc = parse(BAD_README)
        self.assertTrue(doc.placeholder_hits)

    def test_internal_link_validation(self):
        doc = parse(BAD_README)
        # no heading anchor "nonexistent-anchor" exists
        anchors = {a.lower() for a in doc.anchors}
        self.assertNotIn("nonexistent-anchor", anchors)

    def test_language_detection(self):
        self.assertEqual(detect_language(parse(GOOD_README)), "zh")
        self.assertEqual(detect_language(parse("# Title\n\nThis is an English readme with enough words to pass the detection threshold easily.")), "en")

    def test_slugify(self):
        self.assertEqual(slugify("Quick Start"), "quick-start")
        self.assertEqual(slugify("安装 / Installation"), "安装-installation")


class TestRules(unittest.TestCase):
    def test_good_readme_passes_core(self):
        doc = parse(GOOD_README)
        results = apply_rules(doc)
        by_id = {r.rule_id: r for r in results}
        self.assertTrue(by_id["title"].passed)
        self.assertTrue(by_id["license"].passed)
        self.assertTrue(by_id["installation"].passed)
        self.assertTrue(by_id["usage"].passed)
        self.assertTrue(by_id["code_example"].passed)
        self.assertTrue(by_id["no_placeholder"].passed)

    def test_bad_readme_fails_core(self):
        doc = parse(BAD_README)
        results = apply_rules(doc)
        by_id = {r.rule_id: r for r in results}
        self.assertFalse(by_id["no_placeholder"].passed)
        self.assertFalse(by_id["license"].passed)
        self.assertFalse(by_id["internal_links"].passed)

    def test_all_rule_ids_registered(self):
        self.assertTrue(len(RULE_IDS) >= 15)
        ids = {r.rule_id for r in DEFAULT_RULES}
        self.assertEqual(len(ids), len(DEFAULT_RULES))  # unique

    def test_rules_config_disable(self):
        doc = parse(BAD_README)
        cfg = {"license": {"enabled": False}}
        results = apply_rules(doc, cfg)
        ids = {r.rule_id for r in results}
        self.assertNotIn("license", ids)


class TestScorer(unittest.TestCase):
    def test_good_score_high(self):
        doc = parse(GOOD_README)
        sc = score(apply_rules(doc))
        self.assertGreaterEqual(sc.value, 90)
        self.assertIn(sc.grade, ("A", "B"))

    def test_bad_score_low(self):
        doc = parse(BAD_README)
        sc = score(apply_rules(doc))
        self.assertLess(sc.value, 60)

    def test_score_bounds(self):
        doc = parse(GOOD_README)
        sc = score(apply_rules(doc))
        self.assertTrue(0 <= sc.value <= 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
