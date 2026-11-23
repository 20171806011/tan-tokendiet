"""Zero-dependency Model Context Protocol (MCP) stdio server for TAN TokenDiet.

Implements JSON-RPC 2.0 over newline-delimited stdio per MCP specification
(2024-11-05 / 2025-03-26 / 2025-06-18). Logs only to stderr.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, List, Optional, TextIO

from . import __version__
from .analyzer import audit_payload, audit_text
from .minifier import minify_tools_payload
from .pricing import MODELS, estimate_monthly_cost

SUPPORTED_PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")
PRO_URL = "https://20171806011.github.io/tan-tokendiet/"

# Deterministically sorted, compact, prompt-cache-safe tool definitions.
TOOLS: List[Dict[str, Any]] = [
    {
        "description": "Audit AGENTS.md, CLAUDE.md, GEMINI.md, SKILL.md, or system prompt text for token bloat, prompt-cache busters, and monthly LLM cost.",
        "inputSchema": {
            "properties": {
                "cache_hit_rate": {"default": 0.75, "maximum": 1, "minimum": 0, "type": "number"},
                "cache_write_ttl": {"default": "5m", "enum": ["none", "5m", "1h"], "type": "string"},
                "model_id": {"default": "claude-sonnet", "enum": sorted(MODELS.keys()), "type": "string"},
                "source": {"default": "AGENTS.md", "type": "string"},
                "team_size": {"default": 1, "minimum": 1, "type": "integer"},
                "text": {"description": "Raw markdown or prompt text to audit.", "type": "string"},
                "turns_per_day": {"default": 120, "minimum": 1, "type": "integer"},
            },
            "required": ["text"],
            "type": "object",
        },
        "name": "audit_agent_context",
    },
    {
        "description": "Audit an MCP tools JSON array or mcp.json payload across 12 diagnostic rules for token burn and 5m/1h prompt-cache safety.",
        "inputSchema": {
            "properties": {
                "cache_hit_rate": {"default": 0.75, "maximum": 1, "minimum": 0, "type": "number"},
                "cache_write_ttl": {"default": "5m", "enum": ["none", "5m", "1h"], "type": "string"},
                "model_id": {"default": "claude-sonnet", "enum": sorted(MODELS.keys()), "type": "string"},
                "payload": {"description": "MCP tools array, {tools:[...]} object, or JSON string."},
                "source": {"default": "tools.json", "type": "string"},
                "team_size": {"default": 1, "minimum": 1, "type": "integer"},
                "turns_per_day": {"default": 120, "minimum": 1, "type": "integer"},
            },
            "required": ["payload"],
            "type": "object",
        },
        "name": "audit_mcp_schema",
    },
    {
        "description": "Compare monthly USD and GBP input token burn across frontier LLM models with prompt-cache hit and TTL write multipliers.",
        "inputSchema": {
            "properties": {
                "cache_hit_rate": {"default": 0.75, "maximum": 1, "minimum": 0, "type": "number"},
                "cache_write_ttl": {"default": "5m", "enum": ["none", "5m", "1h"], "type": "string"},
                "team_size": {"default": 1, "minimum": 1, "type": "integer"},
                "tokens_per_turn": {"minimum": 1, "type": "integer"},
                "turns_per_day": {"default": 120, "minimum": 1, "type": "integer"},
            },
            "required": ["tokens_per_turn"],
            "type": "object",
        },
        "name": "estimate_context_cost",
    },
    {
        "description": "Compact MCP tool schemas deterministically with 100% JSON Schema structural invariant verification and sorted keys.",
        "inputSchema": {
            "properties": {
                "aggressive": {"default": False, "type": "boolean"},
                "payload": {"description": "MCP tools array, {tools:[...]} object, or JSON string."},
                "sort_tools": {"default": True, "type": "boolean"},
            },
            "required": ["payload"],
            "type": "object",
        },
        "name": "minify_mcp_schema",
    },
]


def _coerce_payload(raw: Any) -> Any:
    if isinstance(raw, str):
        return json.loads(raw)
    return raw


def _call_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if name == "audit_mcp_schema":
        payload = _coerce_payload(args["payload"])
        report = audit_payload(payload, source=str(args.get("source", "tools.json")))
        model_id = str(args.get("model_id", "claude-sonnet"))
        if model_id not in MODELS:
            model_id = "claude-sonnet"
        data = report.to_dict(
            model_id=model_id,
            turns_per_day=max(1, int(args.get("turns_per_day", 120))),
            team_size=max(1, int(args.get("team_size", 1))),
            cache_hit_rate=min(1.0, max(0.0, float(args.get("cache_hit_rate", 0.75)))),
            cache_write_ttl=str(args.get("cache_write_ttl", "5m")),
        )
        data["pro_kit_url"] = PRO_URL
        return data

    if name == "minify_mcp_schema":
        payload = _coerce_payload(args["payload"])
        res = minify_tools_payload(
            payload,
            aggressive=bool(args.get("aggressive", False)),
            sort_tools=bool(args.get("sort_tools", True)),
        )
        return {
            "actions_applied": res.actions_applied,
            "invariants_verified": res.invariants_verified,
            "minified_payload": res.minified_payload,
            "minified_tokens": res.minified_tokens,
            "original_tokens": res.original_tokens,
            "percent_saved": res.percent_saved,
            "pro_kit_url": PRO_URL,
            "tokens_saved": res.tokens_saved,
        }

    if name == "audit_agent_context":
        report = audit_text(str(args["text"]), source=str(args.get("source", "AGENTS.md")))
        model_id = str(args.get("model_id", "claude-sonnet"))
        if model_id not in MODELS:
            model_id = "claude-sonnet"
        data = report.to_dict(
            model_id=model_id,
            turns_per_day=max(1, int(args.get("turns_per_day", 120))),
            team_size=max(1, int(args.get("team_size", 1))),
            cache_hit_rate=min(1.0, max(0.0, float(args.get("cache_hit_rate", 0.75)))),
            cache_write_ttl=str(args.get("cache_write_ttl", "5m")),
        )
        data["pro_kit_url"] = PRO_URL
        return data

    if name == "estimate_context_cost":
        tokens = max(1, int(args["tokens_per_turn"]))
        turns = max(1, int(args.get("turns_per_day", 120)))
        team = max(1, int(args.get("team_size", 1)))
        hit = min(1.0, max(0.0, float(args.get("cache_hit_rate", 0.75))))
        ttl = str(args.get("cache_write_ttl", "5m"))
        by_model = {
            mid: estimate_monthly_cost(
                tokens_per_turn=tokens,
                turns_per_day=turns,
                team_size=team,
                model_id=mid,
                cache_hit_rate=hit,
                cache_write_ttl=ttl,
            )
            for mid in sorted(MODELS.keys())
        }
        return {
            "cache_hit_rate": hit,
            "cache_write_ttl": ttl,
            "models": by_model,
            "pro_kit_url": PRO_URL,
            "team_size": team,
            "tokens_per_turn": tokens,
            "turns_per_day": turns,
        }

    raise KeyError(f"Unknown tool: {name}")


def handle_message(msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Process one JSON-RPC 2.0 request/notification and return response or None."""
    method = msg.get("method")
    req_id = msg.get("id")
    params = msg.get("params") or {}

    # Notifications have no id -> no response emitted
    if req_id is None:
        return None

    if method == "initialize":
        client_ver = str(params.get("protocolVersion", SUPPORTED_PROTOCOLS[0]))
        proto = client_ver if client_ver in SUPPORTED_PROTOCOLS else SUPPORTED_PROTOCOLS[0]
        return {
            "id": req_id,
            "jsonrpc": "2.0",
            "result": {
                "capabilities": {"tools": {"listChanged": False}},
                "protocolVersion": proto,
                "serverInfo": {
                    "name": "tan-tokendiet",
                    "title": "TAN TokenDiet — MCP Schema & Context FinOps",
                    "version": __version__,
                },
            },
        }

    if method == "ping":
        return {"id": req_id, "jsonrpc": "2.0", "result": {}}

    if method == "tools/list":
        return {"id": req_id, "jsonrpc": "2.0", "result": {"tools": TOOLS}}

    if method == "tools/call":
        tool_name = str(params.get("name", ""))
        arguments = params.get("arguments") or {}
        try:
            result = _call_tool(tool_name, arguments)
            return {
                "id": req_id,
                "jsonrpc": "2.0",
                "result": {
                    "content": [{"text": json.dumps(result, sort_keys=True, ensure_ascii=False), "type": "text"}],
                    "isError": False,
                    "structuredContent": result,
                },
            }
        except KeyError as exc:
            return {
                "error": {"code": -32602, "message": str(exc)},
                "id": req_id,
                "jsonrpc": "2.0",
            }
        except Exception as exc:
            return {
                "id": req_id,
                "jsonrpc": "2.0",
                "result": {
                    "content": [{"text": f"Error: {exc}", "type": "text"}],
                    "isError": True,
                },
            }

    return {
        "error": {"code": -32601, "message": f"Method not found: {method}"},
        "id": req_id,
        "jsonrpc": "2.0",
    }


def serve_stdio(stdin: TextIO = sys.stdin, stdout: TextIO = sys.stdout) -> None:
    """Serve MCP JSON-RPC 2.0 requests over newline-delimited stdio."""
    for raw_line in stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as exc:
            resp: Optional[Dict[str, Any]] = {
                "error": {"code": -32700, "message": f"Parse error: {exc}"},
                "id": None,
                "jsonrpc": "2.0",
            }
        else:
            if isinstance(msg, dict):
                resp = handle_message(msg)
            else:
                resp = {
                    "error": {"code": -32600, "message": "Invalid Request"},
                    "id": None,
                    "jsonrpc": "2.0",
                }
        if resp is not None:
            stdout.write(json.dumps(resp, ensure_ascii=False, separators=(",", ":")) + "\n")
            stdout.flush()


def main() -> int:
    serve_stdio()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
