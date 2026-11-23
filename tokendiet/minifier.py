"""Deterministic, structure-preserving JSON Schema & MCP tool compactor."""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Set

from .tokenizer import count_json_tokens

_CODE_FENCE_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
_EXAMPLE_TAIL_RE = re.compile(r"(?:\n+|\s+)(?:Examples?|For example|e\.g\.)\s*:[\s\S]*$", re.IGNORECASE)
_FILLER_PHRASES = [
    (re.compile(r"\bThis tool allows (?:you|the user|the agent) to\b", re.I), ""),
    (re.compile(r"\bUse this tool (?:when you want |whenever you need )?to\b", re.I), ""),
    (re.compile(r"\bPlease note that\b", re.I), "Note:"),
    (re.compile(r"\bMake sure (?:that )?you\b", re.I), "Ensure"),
    (re.compile(r"\bIn order to\b", re.I), "To"),
]


@dataclass
class MinifyResult:
    original_tokens: int
    minified_tokens: int
    tokens_saved: int
    percent_saved: float
    minified_payload: Any
    minified_json: str
    invariants_verified: bool
    actions_applied: List[str]


def _compact_description(text: str, aggressive: bool = False) -> str:
    s = _CODE_FENCE_RE.sub("", text)
    if aggressive:
        s = _EXAMPLE_TAIL_RE.sub("", s)
        for pat, repl in _FILLER_PHRASES:
            s = pat.sub(repl, s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{2,}", " ", s)
    s = s.replace("\n", " ").strip()
    # Clean leading punctuation left by stripped filler
    s = re.sub(r"^[,;:\-\s]+", "", s)
    if s and s[0].islower() and aggressive:
        s = s[0].upper() + s[1:]
    if aggressive and len(s) > 220:
        # Keep first sentence(s) up to ~200 chars cleanly
        sentences = re.split(r"(?<=[.!?])\s+", s)
        kept: List[str] = []
        acc = 0
        for sent in sentences:
            if acc + len(sent) <= 210 or not kept:
                kept.append(sent)
                acc += len(sent) + 1
            else:
                break
        s = " ".join(kept).strip()
    return s


def _clean_schema_node(node: Any, key_name: str = "", aggressive: bool = False, actions: Set[str] | None = None) -> Any:
    if actions is None:
        actions = set()
    if isinstance(node, list):
        return [_clean_schema_node(item, aggressive=aggressive, actions=actions) for item in node]
    if not isinstance(node, dict):
        return node

    out: Dict[str, Any] = {}
    for k in sorted(node.keys()):
        v = node[k]
        if k == "$schema":
            actions.add("stripped $schema metadata")
            continue
        if k == "additionalProperties" and v is False:
            actions.add("stripped redundant additionalProperties: false")
            continue
        if k == "required" and isinstance(v, list) and len(v) == 0:
            actions.add("removed empty required: [] arrays")
            continue
        if k == "title" and isinstance(v, str) and key_name:
            norm_t = re.sub(r"[^a-z0-9]", "", v.lower())
            norm_k = re.sub(r"[^a-z0-9]", "", key_name.lower())
            if norm_t == norm_k:
                actions.add("stripped redundant Pydantic/Zod title fields")
                continue
        if k == "description" and isinstance(v, str):
            compacted = _compact_description(v, aggressive=aggressive)
            if compacted != v:
                actions.add("compacted descriptions & whitespace")
            if compacted:
                out[k] = compacted
            continue
        if k == "properties" and isinstance(v, dict):
            cleaned_props: Dict[str, Any] = {}
            for pk in sorted(v.keys()):
                cleaned_props[pk] = _clean_schema_node(v[pk], key_name=pk, aggressive=aggressive, actions=actions)
            if list(v.keys()) != sorted(v.keys()):
                actions.add("sorted JSON keys deterministically for KV prompt-cache stability")
            out[k] = cleaned_props
            continue
        out[k] = _clean_schema_node(v, key_name=k, aggressive=aggressive, actions=actions)
    return out


def _extract_structural_signature(payload: Any) -> Dict[str, Any]:
    """Extract invariant schema signature: every tool name, property name, type, required set, and enum."""
    tools_list = None
    if isinstance(payload, dict) and isinstance(payload.get("tools"), list):
        tools_list = payload["tools"]
    elif isinstance(payload, list):
        tools_list = payload
    if tools_list is None:
        return {"raw_type": type(payload).__name__}

    sig: Dict[str, Any] = {}
    for item in tools_list:
        if not isinstance(item, dict):
            continue
        fn = item.get("function") if isinstance(item.get("function"), dict) else item
        name = str(fn.get("name", ""))
        schema = fn.get("inputSchema") or fn.get("input_schema") or fn.get("parameters") or {}
        sig[name] = _schema_signature(schema)
    return sig


def _schema_signature(schema: Any) -> Any:
    if not isinstance(schema, dict):
        return schema
    props = schema.get("properties", {})
    req = sorted(schema.get("required", [])) if isinstance(schema.get("required"), list) else []
    out: Dict[str, Any] = {
        "type": schema.get("type"),
        "required": req,
    }
    if "enum" in schema:
        out["enum"] = schema["enum"]
    if isinstance(props, dict):
        out["properties"] = {k: _schema_signature(props[k]) for k in sorted(props.keys())}
    if isinstance(schema.get("items"), dict):
        out["items"] = _schema_signature(schema["items"])
    return out


def minify_tools_payload(payload: Any, aggressive: bool = False, sort_tools: bool = True) -> MinifyResult:
    """Safely compact an MCP / OpenAI / Anthropic tool payload and verify structural invariants."""
    original_tokens = count_json_tokens(payload, compact=True)
    orig_sig = _extract_structural_signature(payload)
    actions: Set[str] = set()

    work = copy.deepcopy(payload)
    cleaned = _clean_schema_node(work, aggressive=aggressive, actions=actions)

    if sort_tools:
        if isinstance(cleaned, dict) and isinstance(cleaned.get("tools"), list):
            before = [t.get("name") or (t.get("function") or {}).get("name", "") for t in cleaned["tools"] if isinstance(t, dict)]
            cleaned["tools"] = sorted(
                cleaned["tools"],
                key=lambda t: str((t.get("name") or (t.get("function") or {}).get("name", "")) if isinstance(t, dict) else ""),
            )
            after = [t.get("name") or (t.get("function") or {}).get("name", "") for t in cleaned["tools"] if isinstance(t, dict)]
            if before != after:
                actions.add("sorted tools alphabetically for deterministic prompt caching")
        elif isinstance(cleaned, list) and all(isinstance(x, dict) for x in cleaned):
            cleaned = sorted(
                cleaned,
                key=lambda t: str(t.get("name") or (t.get("function") or {}).get("name", "")),
            )
            actions.add("sorted tools alphabetically for deterministic prompt caching")

    new_sig = _extract_structural_signature(cleaned)
    invariants_ok = orig_sig == new_sig

    minified_json = json.dumps(cleaned, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    minified_tokens = count_json_tokens(cleaned, compact=True)
    saved = max(0, original_tokens - minified_tokens)
    pct = round((saved / original_tokens * 100.0) if original_tokens else 0.0, 1)

    return MinifyResult(
        original_tokens=original_tokens,
        minified_tokens=minified_tokens,
        tokens_saved=saved,
        percent_saved=pct,
        minified_payload=cleaned,
        minified_json=minified_json,
        invariants_verified=invariants_ok,
        actions_applied=sorted(actions),
    )
