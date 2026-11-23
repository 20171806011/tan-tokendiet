"""Command-line interface for TAN TokenDiet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__
from .analyzer import audit_path
from .minifier import minify_tools_payload
from .pricing import MODELS


def _cmd_audit(args: argparse.Namespace) -> int:
    report = audit_path(args.path)
    data = report.to_dict(
        model_id=args.model,
        turns_per_day=args.turns_per_day,
        team_size=args.team_size,
        cache_hit_rate=args.cache_hit_rate,
    )
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"TAN TokenDiet v{__version__} — Context Audit")
        print(f"Source: {data['source']} ({data['kind']})")
        print(
            f"Health Score: {data['score']}/100 (Grade {data['grade']}) | "
            f"Prompt-Cache Safe: {'YES' if data['prompt_cache_safe'] else 'NO'}"
        )
        print(
            f"Total Tokens/Turn: {data['total_tokens']:,} | "
            f"Estimated Reducible: {data['estimated_reducible_tokens']:,} ({data['reducible_percent']}%)"
        )
        cc = data["cost_current"]
        ca = data["cost_projected_after_diet"]
        print(
            f"Monthly Input Burn ({args.model}, {args.turns_per_day} turns/day x {args.team_size} devs): "
            f"${cc['effective_monthly_usd']:.2f} (£{cc['effective_monthly_gbp']:.2f}) -> "
            f"${ca['effective_monthly_usd']:.2f} (£{ca['effective_monthly_gbp']:.2f}) after diet"
        )
        if data["tools"]:
            print("\nTop Context Consumers:")
            for t in data["tools"][:10]:
                print(f"  - {t['name']:<32} {t['tokens']:>6,} tok (desc {t['description_tokens']}, schema {t['schema_tokens']})")
        if data["findings"]:
            print(f"\nFindings ({len(data['findings'])}):")
            for f in data["findings"][:20]:
                print(f"  [{f['severity'].upper():<8}] {f['rule_id']} ({f['target']}): {f['message']}")
                if f["suggestion"]:
                    print(f"             -> {f['suggestion']}")
        else:
            print("\nNo issues detected. Clean schema!")

    if args.max_tokens is not None and data["total_tokens"] > args.max_tokens:
        return 2
    if args.fail_on_cache_buster and not data["prompt_cache_safe"]:
        return 3
    return 0


def _cmd_minify(args: argparse.Namespace) -> int:
    src = Path(args.file)
    raw = json.loads(src.read_text(encoding="utf-8"))
    res = minify_tools_payload(raw, aggressive=args.aggressive, sort_tools=not args.keep_order)
    if not res.invariants_verified:
        print("ERROR: Structural schema invariant check failed; refusing to emit modified payload.", file=sys.stderr)
        return 1
    output_text = (
        res.minified_json
        if args.compact_json
        else json.dumps(res.minified_payload, indent=2, ensure_ascii=False, sort_keys=True)
    )
    if args.out:
        Path(args.out).write_text(output_text + "\n", encoding="utf-8")
        print(
            f"Wrote compacted schema to {args.out}: "
            f"{res.original_tokens:,} -> {res.minified_tokens:,} tokens "
            f"(saved {res.tokens_saved:,} / {res.percent_saved}%, invariants verified)."
        )
    else:
        print(output_text)
    return 0


def _cmd_diff(args: argparse.Namespace) -> int:
    base = audit_path(args.base)
    head = audit_path(args.head)
    delta = head.total_tokens - base.total_tokens
    pct = round((delta / base.total_tokens * 100.0) if base.total_tokens else 0.0, 1)
    summary = {
        "base": args.base,
        "head": args.head,
        "base_tokens": base.total_tokens,
        "head_tokens": head.total_tokens,
        "delta_tokens": delta,
        "delta_percent": pct,
        "head_cache_safe": head.prompt_cache_safe,
    }
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        sign = "+" if delta > 0 else ""
        print(f"Token Diff: {base.total_tokens:,} -> {head.total_tokens:,} ({sign}{delta:,} tokens / {sign}{pct}%)")
        print(f"Prompt-Cache Safe: {'YES' if head.prompt_cache_safe else 'NO'}")
    if args.max_delta is not None and delta > args.max_delta:
        print(f"Budget exceeded: +{delta} tokens > max allowed +{args.max_delta}", file=sys.stderr)
        return 2
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tokendiet",
        description="TAN TokenDiet — Audit, benchmark, and compact MCP tool schemas & AI agent context files.",
    )
    parser.add_argument("-V", "--version", action="version", version=f"tokendiet {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_audit = sub.add_parser("audit", help="Audit an MCP schema JSON, mcp.json, instruction file, or repository")
    p_audit.add_argument("path", help="File or directory to audit")
    p_audit.add_argument("--model", choices=sorted(MODELS.keys()), default="claude-sonnet")
    p_audit.add_argument("--turns-per-day", type=int, default=120)
    p_audit.add_argument("--team-size", type=int, default=1)
    p_audit.add_argument("--cache-hit-rate", type=float, default=0.0)
    p_audit.add_argument("--max-tokens", type=int, default=None, help="Exit with code 2 if total tokens exceed budget")
    p_audit.add_argument("--fail-on-cache-buster", action="store_true", help="Exit with code 3 if prompt cache busters found")
    p_audit.add_argument("--json", action="store_true", help="Emit JSON output")
    p_audit.set_defaults(func=_cmd_audit)

    p_min = sub.add_parser("minify", help="Safely compact an MCP / LLM tool schema JSON file")
    p_min.add_argument("file", help="Path to JSON tool schema file")
    p_min.add_argument("-o", "--out", help="Output path (prints to stdout if omitted)")
    p_min.add_argument("--aggressive", action="store_true", help="Also trim inline examples & filler phrases in descriptions")
    p_min.add_argument("--compact-json", action="store_true", help="Emit single-line compact JSON")
    p_min.add_argument("--keep-order", action="store_true", help="Keep original tool order instead of alphabetical sorting")
    p_min.set_defaults(func=_cmd_minify)

    p_diff = sub.add_parser("diff", help="Compare token budgets between baseline and modified files/dirs (CI gate)")
    p_diff.add_argument("base", help="Baseline file or directory")
    p_diff.add_argument("head", help="Modified file or directory")
    p_diff.add_argument("--max-delta", type=int, default=None, help="Fail with exit code 2 if token increase exceeds limit")
    p_diff.add_argument("--json", action="store_true", help="Emit JSON output")
    p_diff.set_defaults(func=_cmd_diff)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
