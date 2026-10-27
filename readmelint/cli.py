"""Command line interface for ReadmeLint."""

from __future__ import annotations

import argparse
import glob
import os
import sys
from typing import List, Optional, Tuple

from . import __version__
from .md import parse, detect_language
from .rules import apply_rules, load_rules_config
from .scorer import score
from .report import to_text, to_json, to_markdown, aggregate_summary, set_color


def _find_readmes(directory: str, recursive: bool = False) -> List[str]:
    pattern = os.path.join(directory, "**", "README*.md") if recursive \
        else os.path.join(directory, "README*.md")
    found = glob.glob(pattern, recursive=recursive)
    # also catch lower-case variants not matched by README* (rare)
    found += glob.glob(os.path.join(directory, "readme*.md"))
    # dedupe, keep .md only, sorted
    seen = set()
    out = []
    for f in sorted(found):
        if f.lower().endswith(".md") and f not in seen:
            seen.add(f)
            out.append(f)
    return out


def _best_readme(directory: str) -> Optional[str]:
    exact = os.path.join(directory, "README.md")
    if os.path.isfile(exact):
        return exact
    others = _find_readmes(directory)
    return others[0] if others else None


def _lint_path(path: str, fmt: str, lang_opt: str, rules_cfg, color: bool) -> Tuple[str, str, object, object]:
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    doc = parse(text)
    lang = lang_opt if lang_opt in ("zh", "en") else detect_language(doc)
    results = apply_rules(doc, rules_cfg)
    sc = score(results)
    set_color(color)

    if fmt == "json":
        out = to_json(path, sc, results, lang)
    elif fmt == "md":
        out = to_markdown(path, sc, results, lang)
    else:
        out = to_text(path, sc, results, lang)
    return path, lang, sc, out


def cmd_lint(args: argparse.Namespace) -> int:
    rules_cfg = load_rules_config(args.rules) if args.rules else None
    color = (not args.no_color) and sys.stdout.isatty()

    if os.path.isfile(args.path):
        targets = [args.path]
    elif os.path.isdir(args.path):
        targets = _find_readmes(args.path)
        if not targets:
            print(f"在 {args.path} 中未找到 README 文件", file=sys.stderr)
            return 2
    else:
        print(f"路径不存在: {args.path}", file=sys.stderr)
        return 2

    exit_code = 0
    outputs: List[str] = []
    for t in targets:
        path, lang, sc, out = _lint_path(t, args.format, args.lang, rules_cfg, color)
        outputs.append(out)
        if args.min_score is not None and sc.value < args.min_score:
            exit_code = 1
        if args.strict and sc.blockers_failed > 0:
            exit_code = 1

    full = "\n".join(outputs)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(full)
        if not args.quiet:
            print(f"报告已写入: {args.report}")
    else:
        print(full)

    return exit_code


def cmd_batch(args: argparse.Namespace) -> int:
    rules_cfg = load_rules_config(args.rules) if args.rules else None
    color = (not args.no_color) and sys.stdout.isatty()

    rows = []
    details = []
    for entry in sorted(os.scandir(args.path), key=lambda e: e.name):
        if not entry.is_dir():
            continue
        readme = _best_readme(entry.path)
        if not readme:
            continue
        _p, lang, sc, out = _lint_path(readme, args.format, args.lang, rules_cfg, color)
        repo_name = entry.name
        rows.append({"path": repo_name, "score": sc.value, "grade": sc.grade})
        details.append(out)

    if not rows:
        print(f"在 {args.path} 的子目录中未找到任何 README", file=sys.stderr)
        return 2

    exit_code = 0
    if args.format == "json":
        payload = {"repositories": rows,
                   "average": round(sum(r["score"] for r in rows) / len(rows))}
        output = __import__("json").dumps(payload, ensure_ascii=False, indent=2)
    elif args.format == "md":
        output = "# 📊 ReadmeLint 批量报告\n\n" + "\n".join(details)
    else:
        output = aggregate_summary(rows) + "\n"

    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(output)
        if not args.quiet:
            print(f"批量报告已写入: {args.report}")
    else:
        print(output)

    if args.min_score is not None and any(r["score"] < args.min_score for r in rows):
        exit_code = 1
    return exit_code


def build_parser() -> argparse.ArgumentParser:
    # Shared options so they may appear either before or after the subcommand.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--version", action="version", version=f"readmelint {__version__}")
    common.add_argument("--rules", help="自定义规则 JSON 配置文件路径")
    common.add_argument("--format", choices=["text", "json", "md"], default="text", help="输出格式 (默认 text)")
    common.add_argument("--lang", choices=["auto", "zh", "en"], default="auto", help="语言 (默认自动检测)")
    common.add_argument("--min-score", type=int, default=None, help="低于该分数则退出码为 1 (CI 门禁)")
    common.add_argument("--strict", action="store_true", help="存在未通过的阻断级规则时退出码为 1")
    common.add_argument("--no-color", action="store_true", help="关闭 ANSI 颜色")
    common.add_argument("--report", help="将报告写入指定文件而非标准输出")
    common.add_argument("--quiet", action="store_true", help="仅输出报告文件路径等必要信息")

    p = argparse.ArgumentParser(
        prog="readmelint",
        parents=[common],
        description="零依赖的 README 质量评分与检测工具 (ReadmeLint)",
    )

    sub = p.add_subparsers(dest="command", required=True)
    pl = sub.add_parser("lint", parents=[common], help="检测单个文件或目录下的 README")
    pl.add_argument("path", help="README 文件路径或包含 README 的目录")
    pl.set_defaults(func=cmd_lint)

    pb = sub.add_parser("batch", parents=[common], help="批量扫描目录下各子仓库的 README")
    pb.add_argument("path", help="包含多个仓库子目录的根目录")
    pb.set_defaults(func=cmd_batch)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
