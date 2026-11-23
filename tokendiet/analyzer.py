"""12-rule diagnostic auditor for MCP tool schemas, mcp.json, and AI agent instruction files."""

from __future__ import annotations

import json
import os
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .pricing import estimate_monthly_cost
from .tokenizer import count_json_tokens, count_tokens

AGENT_CONTEXT_FILENAMES = {
    "AGENTS.md",
    "CLAUDE.md",
    "SKILL.md",
    "GEMINI.md",
    ".cursorrules",
    ".windsurfrules",
    "copilot-instructions.md",
    "mcp.json",
    ".mcp.json",
    "claude_desktop_config.json",
    "tools.json",
}

_CACHE_BUSTER_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    ("ISO timestamp/date", re.compile(r"\b20\d{2}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?)?\b")),
    ("Dynamic template date/time", re.compile(r"\{\{\s*(?:now|date|time|timestamp|today|current_date|uuid|random)\b[^}]*\}\}", re.I)),
    ("Runtime JS/Python clock call", re.compile(r"\b(?:Date\.now\(\)|new Date\(\)|datetime\.now\(\)|time\.time\(\)|uuid4\(\))\b")),
    ("UUID v4 literal", re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b", re.I)),
]

_EXAMPLE_BLOCK_PATTERN = re.compile(r"(```|example\s*:|for example|e\.g\.,?\s*\{|<example>)", re.I)


@dataclass
class Finding:
    rule_id: str
    severity: str  # "critical" | "warning" | "info"
    target: str
    message: str
    estimated_wasted_tokens: int = 0
    suggestion: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ToolMetric:
    name: str
    tokens: int
    description_tokens: int
    schema_tokens: int
    param_count: int
    max_depth: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AuditReport:
    source: str
    kind: str  # "mcp_tools" | "mcp_config" | "agent_instructions" | "directory"
    total_tokens: int
    tool_count: int
    score: int  # 0–100 health score
    grade: str  # A / B / C / D / F
    estimated_reducible_tokens: int
    prompt_cache_safe: bool
    tools: List[ToolMetric] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)
    files_scanned: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(
        self,
        model_id: str = "claude-sonnet",
        turns_per_day: int = 120,
        team_size: int = 1,
        cache_hit_rate: float = 0.0,
        cache_write_ttl: str = "none",
    ) -> Dict[str, Any]:
        cost = estimate_monthly_cost(
            self.total_tokens,
            turns_per_day=turns_per_day,
            team_size=team_size,
            model_id=model_id,
            cache_hit_rate=cache_hit_rate,
            cache_write_ttl=cache_write_ttl,
        )
        projected_after = max(0, self.total_tokens - self.estimated_reducible_tokens)
        cost_after = estimate_monthly_cost(
            projected_after,
            turns_per_day=turns_per_day,
            team_size=team_size,
            model_id=model_id,
            cache_hit_rate=cache_hit_rate,
            cache_write_ttl=cache_write_ttl,
        )
        return {
            "source": self.source,
            "kind": self.kind,
            "total_tokens": self.total_tokens,
            "tool_count": self.tool_count,
            "score": self.score,
            "grade": self.grade,
            "estimated_reducible_tokens": self.estimated_reducible_tokens,
            "reducible_percent": round(
                (self.estimated_reducible_tokens / self.total_tokens * 100.0) if self.total_tokens else 0.0,
                1,
            ),
            "prompt_cache_safe": self.prompt_cache_safe,
            "cost_current": cost,
            "cost_projected_after_diet": cost_after,
            "tools": [t.to_dict() for t in self.tools],
            "findings": [f.to_dict() for f in self.findings],
            "files_scanned": self.files_scanned,
        }


def _schema_depth(obj: Any, current: int = 0) -> int:
    if isinstance(obj, dict):
        if not obj:
            return current
        return max(_schema_depth(v, current + 1) for v in obj.values())
    if isinstance(obj, list):
        if not obj:
            return current
        return max(_schema_depth(v, current) for v in obj)
    return current


def _extract_tools(payload: Any) -> Optional[List[Dict[str, Any]]]:
    """Extract normalized list of tool definitions from MCP, OpenAI, Anthropic, or Gemini schemas."""
    if isinstance(payload, list) and payload and all(isinstance(x, dict) for x in payload):
        if any("name" in x or "function" in x or "functionDeclarations" in x for x in payload):
            return _normalize_tool_list(payload)
        return None

    if isinstance(payload, dict):
        if isinstance(payload.get("tools"), list):
            return _normalize_tool_list(payload["tools"])
        if isinstance(payload.get("result"), dict) and isinstance(payload["result"].get("tools"), list):
            return _normalize_tool_list(payload["result"]["tools"])
        if isinstance(payload.get("functionDeclarations"), list):
            return _normalize_tool_list(payload["functionDeclarations"])
    return None


def _normalize_tool_list(raw_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for item in raw_tools:
        if not isinstance(item, dict):
            continue
        if "function" in item and isinstance(item["function"], dict):
            fn = item["function"]
            normalized.append(
                {
                    "name": str(fn.get("name", "unnamed")),
                    "description": str(fn.get("description", "")),
                    "inputSchema": fn.get("parameters", {}),
                    "_raw": item,
                }
            )
        elif "functionDeclarations" in item and isinstance(item["functionDeclarations"], list):
            for decl in item["functionDeclarations"]:
                if isinstance(decl, dict):
                    normalized.append(
                        {
                            "name": str(decl.get("name", "unnamed")),
                            "description": str(decl.get("description", "")),
                            "inputSchema": decl.get("parameters", {}),
                            "_raw": decl,
                        }
                    )
        else:
            schema = item.get("inputSchema") or item.get("input_schema") or item.get("parameters") or {}
            normalized.append(
                {
                    "name": str(item.get("name", "unnamed")),
                    "description": str(item.get("description", "")),
                    "inputSchema": schema if isinstance(schema, dict) else {},
                    "_raw": item,
                }
            )
    return normalized


def _score_from_findings(total_tokens: int, findings: List[Finding], cache_safe: bool) -> Tuple[int, str]:
    score = 100
    for f in findings:
        if f.severity == "critical":
            score -= 14
        elif f.severity == "warning":
            score -= 6
        else:
            score -= 2
    if not cache_safe:
        score -= 10
    if total_tokens > 12000:
        score -= 15
    elif total_tokens > 4000:
        score -= 6
    score = max(0, min(100, score))
    if score >= 90:
        grade = "A"
    elif score >= 78:
        grade = "B"
    elif score >= 62:
        grade = "C"
    elif score >= 45:
        grade = "D"
    else:
        grade = "F"
    return score, grade


def _walk_properties(schema: Any, tool_name: str, findings: List[Finding], prefix: str = "") -> Tuple[int, int]:
    """Inspect schema properties for boilerplate, oversized descriptions, and large enums.
    Returns (param_count, estimated_wasted_tokens).
    """
    if not isinstance(schema, dict):
        return 0, 0

    wasted = 0
    param_count = 0

    # TD003: Redundant boilerplate
    if schema.get("additionalProperties") is False:
        wasted += 4
        findings.append(
            Finding(
                rule_id="TD003",
                severity="info",
                target=f"{tool_name}{prefix}",
                message="Redundant `additionalProperties: false` adds tokens on every turn.",
                estimated_wasted_tokens=4,
                suggestion="Strip `additionalProperties: false` from model-facing schema (validate server-side).",
            )
        )
    if "required" in schema and isinstance(schema["required"], list) and len(schema["required"]) == 0:
        wasted += 4
        findings.append(
            Finding(
                rule_id="TD003",
                severity="info",
                target=f"{tool_name}{prefix}",
                message="Empty `required: []` array is redundant in JSON Schema.",
                estimated_wasted_tokens=4,
                suggestion="Remove empty `required` arrays.",
            )
        )
    if "$schema" in schema:
        wasted += 12
        findings.append(
            Finding(
                rule_id="TD003",
                severity="info",
                target=f"{tool_name}{prefix}",
                message="JSON Schema `$schema` URI is unnecessary in LLM tool payloads.",
                estimated_wasted_tokens=12,
                suggestion="Remove `$schema` metadata before registering tools with the LLM.",
            )
        )

    # TD010: Large enum
    enum_vals = schema.get("enum")
    if isinstance(enum_vals, list) and len(enum_vals) >= 15:
        enum_toks = count_json_tokens(enum_vals)
        waste_est = int(enum_toks * 0.6)
        wasted += waste_est
        findings.append(
            Finding(
                rule_id="TD010",
                severity="warning",
                target=f"{tool_name}{prefix}",
                message=f"Large inline enum ({len(enum_vals)} values, ~{enum_toks} tokens) re-sent every turn.",
                estimated_wasted_tokens=waste_est,
                suggestion="Accept a validated string or expose valid values via a dedicated lookup resource.",
            )
        )

    props = schema.get("properties")
    if isinstance(props, dict):
        keys = list(props.keys())
        if len(keys) >= 3 and keys != sorted(keys):
            findings.append(
                Finding(
                    rule_id="TD006",
                    severity="info",
                    target=f"{tool_name}{prefix}",
                    message="Property keys are unsorted; non-deterministic key order can invalidate KV prompt caches.",
                    estimated_wasted_tokens=0,
                    suggestion="Sort JSON keys deterministically with `tokendiet minify`.",
                )
            )
        for prop_name, prop_def in props.items():
            param_count += 1
            if not isinstance(prop_def, dict):
                continue
            # Redundant title identical to key name (common Pydantic/Zod output)
            title = prop_def.get("title")
            if isinstance(title, str):
                norm_title = re.sub(r"[^a-z0-9]", "", title.lower())
                norm_key = re.sub(r"[^a-z0-9]", "", prop_name.lower())
                if norm_title == norm_key:
                    t_waste = count_tokens(title) + 3
                    wasted += t_waste
                    findings.append(
                        Finding(
                            rule_id="TD003",
                            severity="info",
                            target=f"{tool_name}.{prop_name}",
                            message=f"Redundant `title: \"{title}\"` duplicates property name `{prop_name}` (typical Pydantic/Zod overhead).",
                            estimated_wasted_tokens=t_waste,
                            suggestion="Strip auto-generated `title` annotations matching the field name.",
                        )
                    )
            # TD002: Oversized parameter description
            pdesc = prop_def.get("description")
            if isinstance(pdesc, str):
                ptoks = count_tokens(pdesc)
                if ptoks > 50:
                    w = ptoks - 25
                    wasted += w
                    findings.append(
                        Finding(
                            rule_id="TD002",
                            severity="warning",
                            target=f"{tool_name}.{prop_name}",
                            message=f"Parameter description is {ptoks} tokens (recommended <= 35 tokens).",
                            estimated_wasted_tokens=w,
                            suggestion="Condense to a 1-sentence specification; move examples to documentation.",
                        )
                    )
                if _EXAMPLE_BLOCK_PATTERN.search(pdesc):
                    ex_w = max(8, int(ptoks * 0.35))
                    wasted += ex_w
                    findings.append(
                        Finding(
                            rule_id="TD008",
                            severity="info",
                            target=f"{tool_name}.{prop_name}",
                            message="Inline examples/markdown detected inside parameter description.",
                            estimated_wasted_tokens=ex_w,
                            suggestion="Remove inline examples from schema descriptions unless essential for formatting.",
                        )
                    )
            sub_cnt, sub_w = _walk_properties(prop_def, tool_name, findings, prefix=f"{prefix}.{prop_name}")
            param_count += sub_cnt
            wasted += sub_w

    items = schema.get("items")
    if isinstance(items, dict):
        sub_cnt, sub_w = _walk_properties(items, tool_name, findings, prefix=f"{prefix}[]")
        param_count += sub_cnt
        wasted += sub_w

    return param_count, wasted


def audit_payload(payload: Any, source: str = "<input>") -> AuditReport:
    """Audit a parsed JSON payload (MCP tools/list, OpenAI/Anthropic tools, or mcp.json)."""
    findings: List[Finding] = []
    tools_metrics: List[ToolMetric] = []
    total_reducible = 0
    cache_safe = True

    tools = _extract_tools(payload)
    if tools is not None:
        raw_str = json.dumps(payload, ensure_ascii=False)
        total_tokens = count_json_tokens(payload, compact=True)

        # TD004: Total context threshold
        if total_tokens > 12000:
            findings.append(
                Finding(
                    rule_id="TD004",
                    severity="critical",
                    target=source,
                    message=f"Tool schema payload consumes ~{total_tokens:,} tokens on EVERY turn (>12,000 critical threshold).",
                    estimated_wasted_tokens=int(total_tokens * 0.3),
                    suggestion="Enable lazy/deferred tool loading, split MCP servers by task profile, and compact descriptions.",
                )
            )
        elif total_tokens > 4000:
            findings.append(
                Finding(
                    rule_id="TD004",
                    severity="warning",
                    target=source,
                    message=f"Tool schema payload consumes ~{total_tokens:,} tokens per turn (>4,000 warning threshold).",
                    estimated_wasted_tokens=int(total_tokens * 0.2),
                    suggestion="Compact verbose tool descriptions and strip auto-generated schema metadata.",
                )
            )

        # TD005: Cache-busting dynamic tokens inside schemas
        for label, pat in _CACHE_BUSTER_PATTERNS:
            matches = pat.findall(raw_str)
            if matches:
                cache_safe = False
                findings.append(
                    Finding(
                        rule_id="TD005",
                        severity="critical",
                        target=source,
                        message=f"Prompt-cache-busting {label} detected ({len(matches)} occurrence(s)) inside tool definitions.",
                        estimated_wasted_tokens=0,
                        suggestion="Remove dynamic timestamps/UUIDs from tool definitions so provider KV caches achieve 90% input discount.",
                    )
                )

        # TD006: Unsorted tools list
        tool_names = [t["name"] for t in tools]
        if len(tool_names) >= 3 and tool_names != sorted(tool_names):
            findings.append(
                Finding(
                    rule_id="TD006",
                    severity="warning",
                    target=source,
                    message="Tools array is not sorted alphabetically by name; dynamic registration order breaks KV prefix caching.",
                    estimated_wasted_tokens=0,
                    suggestion="Sort tools deterministically by name before sending to the LLM API.",
                )
            )

        # TD011: Overlapping / duplicate tool names or near-identical prefixes
        name_counts = Counter(tool_names)
        for dup_name, cnt in name_counts.items():
            if cnt > 1:
                findings.append(
                    Finding(
                        rule_id="TD011",
                        severity="critical",
                        target=dup_name,
                        message=f"Duplicate tool name `{dup_name}` registered {cnt} times.",
                        estimated_wasted_tokens=80 * (cnt - 1),
                        suggestion="Deduplicate tool definitions across connected MCP servers.",
                    )
                )

        # TD007: Repeated boilerplate sentences across >=3 tools
        sentence_counts: Counter[str] = Counter()
        for t in tools:
            desc = t["description"]
            for sent in re.split(r"(?<=[.!?])\s+|\n+", desc):
                s = sent.strip()
                if len(s) >= 35:
                    sentence_counts[s] += 1
        for sent, cnt in sentence_counts.items():
            if cnt >= 3:
                w = count_tokens(sent) * (cnt - 1)
                total_reducible += w
                findings.append(
                    Finding(
                        rule_id="TD007",
                        severity="warning",
                        target=source,
                        message=f"Boilerplate instruction repeated across {cnt} tools (~{w} redundant tokens): \"{sent[:70]}...\"",
                        estimated_wasted_tokens=w,
                        suggestion="Move shared rules into a single concise system instruction instead of repeating per tool.",
                    )
                )

        # Per-tool inspection
        for t in tools:
            tname = t["name"]
            desc = t["description"]
            schema = t["inputSchema"]
            desc_toks = count_tokens(desc)
            schema_toks = count_json_tokens(schema, compact=True)
            t_toks = count_json_tokens(t["_raw"], compact=True)
            depth = _schema_depth(schema)

            if desc_toks > 120:
                w = desc_toks - 60
                total_reducible += w
                findings.append(
                    Finding(
                        rule_id="TD001",
                        severity="warning" if desc_toks <= 250 else "critical",
                        target=tname,
                        message=f"Tool description is {desc_toks} tokens (target <= 80 tokens).",
                        estimated_wasted_tokens=w,
                        suggestion="Keep tool description to 1–2 crisp sentences stating purpose and key constraint.",
                    )
                )

            if _EXAMPLE_BLOCK_PATTERN.search(desc):
                w = max(15, int(desc_toks * 0.35))
                total_reducible += w
                findings.append(
                    Finding(
                        rule_id="TD008",
                        severity="warning",
                        target=tname,
                        message="Markdown code fence or inline examples embedded inside tool description.",
                        estimated_wasted_tokens=w,
                        suggestion="Strip examples from always-loaded tool schemas; expose docs on-demand via MCP resources.",
                    )
                )

            if depth >= 5:
                findings.append(
                    Finding(
                        rule_id="TD009",
                        severity="warning",
                        target=tname,
                        message=f"Deeply nested JSON schema (depth {depth}) increases token overhead and argument hallucination risk.",
                        estimated_wasted_tokens=20,
                        suggestion="Flatten nested input objects where possible.",
                    )
                )
                total_reducible += 20

            param_cnt, prop_waste = _walk_properties(schema, tname, findings)
            total_reducible += prop_waste

            tools_metrics.append(
                ToolMetric(
                    name=tname,
                    tokens=t_toks,
                    description_tokens=desc_toks,
                    schema_tokens=schema_toks,
                    param_count=param_cnt,
                    max_depth=depth,
                )
            )

        tools_metrics.sort(key=lambda m: -m.tokens)
        total_reducible = min(total_reducible, int(total_tokens * 0.75))
        score, grade = _score_from_findings(total_tokens, findings, cache_safe)
        return AuditReport(
            source=source,
            kind="mcp_tools",
            total_tokens=total_tokens,
            tool_count=len(tools_metrics),
            score=score,
            grade=grade,
            estimated_reducible_tokens=total_reducible,
            prompt_cache_safe=cache_safe,
            tools=tools_metrics,
            findings=findings,
        )

    # Check if this is an mcpServers config (mcp.json / claude_desktop_config.json)
    if isinstance(payload, dict) and ("mcpServers" in payload or "servers" in payload):
        servers = payload.get("mcpServers") or payload.get("servers") or {}
        if isinstance(servers, dict):
            server_count = len(servers)
            # Empirical average: ~1,200–1,800 tokens per connected MCP server in runtime tools/list
            est_runtime_tokens = server_count * 1450
            if server_count >= 8:
                findings.append(
                    Finding(
                        rule_id="TD004",
                        severity="critical",
                        target=source,
                        message=f"{server_count} always-on MCP servers configured (~{est_runtime_tokens:,} estimated runtime schema tokens per turn).",
                        estimated_wasted_tokens=int(est_runtime_tokens * 0.45),
                        suggestion="Group MCP servers into task-specific profiles instead of loading all servers into every session.",
                    )
                )
                total_reducible = int(est_runtime_tokens * 0.45)
            elif server_count >= 4:
                findings.append(
                    Finding(
                        rule_id="TD004",
                        severity="warning",
                        target=source,
                        message=f"{server_count} always-on MCP servers configured (~{est_runtime_tokens:,} estimated runtime schema tokens per turn).",
                        estimated_wasted_tokens=int(est_runtime_tokens * 0.30),
                        suggestion="Audit each server's `tools/list` output and disable unused tools.",
                    )
                )
                total_reducible = int(est_runtime_tokens * 0.30)

            for sname, sdef in servers.items():
                tools_metrics.append(
                    ToolMetric(
                        name=f"server:{sname}",
                        tokens=1450,
                        description_tokens=0,
                        schema_tokens=1450,
                        param_count=len(sdef.get("args", [])) if isinstance(sdef, dict) else 0,
                        max_depth=1,
                    )
                )
            score, grade = _score_from_findings(est_runtime_tokens, findings, True)
            return AuditReport(
                source=source,
                kind="mcp_config",
                total_tokens=est_runtime_tokens,
                tool_count=server_count,
                score=score,
                grade=grade,
                estimated_reducible_tokens=total_reducible,
                prompt_cache_safe=True,
                tools=tools_metrics,
                findings=findings,
            )

    # Fallback: treat JSON as plain text
    return audit_text(json.dumps(payload, indent=2, ensure_ascii=False), source=source)


def audit_text(text: str, source: str = "<input>") -> AuditReport:
    """Audit raw text — auto-detects JSON schemas or Markdown/instruction files."""
    stripped = text.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, (dict, list)):
                if _extract_tools(parsed) is not None or (
                    isinstance(parsed, dict) and ("mcpServers" in parsed or "servers" in parsed)
                ):
                    return audit_payload(parsed, source=source)
        except json.JSONDecodeError:
            pass

    total_tokens = count_tokens(text)
    findings: List[Finding] = []
    cache_safe = True
    wasted = 0

    # TD005: Prompt-cache-busting dynamic tokens in system/agent instructions
    for label, pat in _CACHE_BUSTER_PATTERNS:
        hits = pat.findall(text)
        if hits:
            cache_safe = False
            findings.append(
                Finding(
                    rule_id="TD005",
                    severity="critical",
                    target=source,
                    message=f"Prompt-cache-busting {label} found ({len(hits)}x) in static instruction file.",
                    estimated_wasted_tokens=0,
                    suggestion="Move timestamps/session IDs to the trailing user message rather than the system prefix.",
                )
            )

    # TD004: Oversized always-loaded instruction file
    if total_tokens > 6000:
        w = int(total_tokens * 0.35)
        wasted += w
        findings.append(
            Finding(
                rule_id="TD004",
                severity="critical",
                target=source,
                message=f"Instruction file is ~{total_tokens:,} tokens; re-sent on every agent turn.",
                estimated_wasted_tokens=w,
                suggestion="Split into a slim core (<1,500 tokens) plus on-demand reference files loaded only when needed.",
            )
        )
    elif total_tokens > 2500:
        w = int(total_tokens * 0.25)
        wasted += w
        findings.append(
            Finding(
                rule_id="TD004",
                severity="warning",
                target=source,
                message=f"Instruction file is ~{total_tokens:,} tokens (recommended <= 2,000 tokens for always-loaded context).",
                estimated_wasted_tokens=w,
                suggestion="Extract detailed checklists and code samples into linked reference docs.",
            )
        )

    # TD012: Excess blank lines / verbose ASCII tables / large fenced examples
    blank_runs = len(re.findall(r"\n{3,}", text))
    fenced_blocks = re.findall(r"```[\s\S]*?```", text)
    fenced_tokens = sum(count_tokens(b) for b in fenced_blocks)
    if fenced_tokens > 600:
        w = int(fenced_tokens * 0.5)
        wasted += w
        findings.append(
            Finding(
                rule_id="TD008",
                severity="warning",
                target=source,
                message=f"Fenced code blocks account for ~{fenced_tokens:,} tokens ({len(fenced_blocks)} blocks) in always-loaded context.",
                estimated_wasted_tokens=w,
                suggestion="Replace long inline code templates with pointers to repo files.",
            )
        )
    if blank_runs >= 5:
        w = blank_runs * 2
        wasted += w
        findings.append(
            Finding(
                rule_id="TD012",
                severity="info",
                target=source,
                message=f"{blank_runs} excessive multi-blank-line gaps and formatting padding detected.",
                estimated_wasted_tokens=w,
                suggestion="Normalize whitespace and trim decorative dividers.",
            )
        )

    # Duplicate lines / repeated headings
    lines = [ln.strip() for ln in text.splitlines() if len(ln.strip()) >= 40]
    dups = [ln for ln, c in Counter(lines).items() if c >= 2]
    if dups:
        dw = sum(count_tokens(d) for d in dups)
        wasted += dw
        findings.append(
            Finding(
                rule_id="TD007",
                severity="warning",
                target=source,
                message=f"{len(dups)} duplicated long instruction lines detected (~{dw} redundant tokens).",
                estimated_wasted_tokens=dw,
                suggestion="Deduplicate repeated directives.",
            )
        )

    wasted = min(wasted, int(total_tokens * 0.7))
    score, grade = _score_from_findings(total_tokens, findings, cache_safe)
    return AuditReport(
        source=source,
        kind="agent_instructions",
        total_tokens=total_tokens,
        tool_count=0,
        score=score,
        grade=grade,
        estimated_reducible_tokens=wasted,
        prompt_cache_safe=cache_safe,
        findings=findings,
    )


def audit_path(target_path: str | Path) -> AuditReport:
    """Audit a single file or recursively discover agent/MCP context files in a directory."""
    p = Path(target_path)
    if p.is_file():
        return audit_text(p.read_text(encoding="utf-8", errors="replace"), source=str(p))

    if not p.is_dir():
        raise FileNotFoundError(f"Path not found: {target_path}")

    scanned: List[Dict[str, Any]] = []
    all_findings: List[Finding] = []
    all_tools: List[ToolMetric] = []
    total_tokens = 0
    total_reducible = 0
    cache_safe = True
    tool_count = 0

    skip_dirs = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next", "target"}
    for root, dirs, files in os.walk(p):
        dirs[:] = [d for d in sorted(dirs) if d not in skip_dirs]
        for fname in sorted(files):
            fpath = Path(root) / fname
            if fname in AGENT_CONTEXT_FILENAMES or fname.endswith(".mcp.json") or fname.endswith(".tools.json"):
                rep = audit_text(fpath.read_text(encoding="utf-8", errors="replace"), source=str(fpath))
                total_tokens += rep.total_tokens
                total_reducible += rep.estimated_reducible_tokens
                tool_count += rep.tool_count
                cache_safe = cache_safe and rep.prompt_cache_safe
                all_findings.extend(rep.findings)
                all_tools.extend(rep.tools)
                scanned.append(
                    {
                        "path": str(fpath.relative_to(p)),
                        "kind": rep.kind,
                        "tokens": rep.total_tokens,
                        "reducible_tokens": rep.estimated_reducible_tokens,
                        "findings": len(rep.findings),
                    }
                )

    all_tools.sort(key=lambda t: -t.tokens)
    score, grade = _score_from_findings(total_tokens, all_findings, cache_safe)
    return AuditReport(
        source=str(p),
        kind="directory",
        total_tokens=total_tokens,
        tool_count=tool_count,
        score=score,
        grade=grade,
        estimated_reducible_tokens=total_reducible,
        prompt_cache_safe=cache_safe,
        tools=all_tools,
        findings=all_findings,
        files_scanned=scanned,
    )
