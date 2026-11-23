"""Zero-dependency BPE-calibrated LLM token estimator.

Designed for JSON schemas, MCP tool definitions, code, Markdown, and CJK text.
Calibrated against cl100k_base / o200k_base tokenization ratios without requiring
native binary wheels or network downloads.
"""

from __future__ import annotations

import json
import math
import re
from typing import Any

# Tokenization regex approximating cl100k/o200k segmentation:
# - CJK ideographs (~1.3-1.6 tokens each in BPE; we model per character)
# - camelCase / snake_case identifiers split into sub-tokens
# - numbers in 1-3 digit chunks
# - JSON structural punctuation clusters (e.g. `": "`, `",`, `{\n  `)
_TOKEN_PATTERN = re.compile(
    r"""
    [\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]   # CJK / Kana / Hangul
    | [A-Za-z]+                                  # ASCII word run
    | \d{1,3}                                    # 1-3 digit chunks
    | \s+                                        # whitespace run
    | [^\sA-Za-z0-9\u4e00-\u9fff]+               # punctuation cluster
    """,
    re.VERBOSE,
)

_CAMEL_SPLIT = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)|\d+")


def count_tokens(text: str) -> int:
    """Estimate BPE token count for arbitrary text or serialized JSON."""
    if not text:
        return 0

    total = 0.0
    for match in _TOKEN_PATTERN.finditer(text):
        piece = match.group(0)
        first = piece[0]

        # CJK characters average ~1.15–1.5 tokens in modern BPE vocabularies
        if "\u4e00" <= first <= "\u9fff" or "\u3040" <= first <= "\u30ff" or "\uac00" <= first <= "\ud7af":
            total += 1.25
            continue

        # Whitespace runs: single space usually merges with next word; newlines/indent add tokens
        if first.isspace():
            newlines = piece.count("\n")
            if newlines > 0:
                total += newlines * 0.85
                indent_spaces = len(piece) - newlines
                if indent_spaces >= 4:
                    total += math.ceil(indent_spaces / 4) * 0.4
            elif len(piece) > 1:
                total += math.ceil(len(piece) / 4) * 0.5
            continue

        # ASCII words / camelCase identifiers
        if first.isalpha():
            parts = _CAMEL_SPLIT.findall(piece)
            if len(parts) > 1:
                for p in parts:
                    total += 1.0 if len(p) <= 7 else math.ceil(len(p) / 4.5)
            else:
                if len(piece) <= 6:
                    total += 1.0
                elif len(piece) <= 12:
                    total += 1.35
                else:
                    total += math.ceil(len(piece) / 4.2)
            continue

        # Digits (already chunked to <=3 digits)
        if first.isdigit():
            total += 1.0
            continue

        # Punctuation clusters (JSON delimiters often merge in BPE like `": "`, `"},`)
        plen = len(piece)
        if plen <= 2:
            total += 0.85
        else:
            total += math.ceil(plen / 2.0) * 0.85

    return max(1, int(round(total)))


def count_json_tokens(obj: Any, compact: bool = True) -> int:
    """Count tokens for a JSON-serializable object."""
    if compact:
        serialized = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    else:
        serialized = json.dumps(obj, ensure_ascii=False, indent=2)
    return count_tokens(serialized)
