"""Unit tests for the TAN TokenDiet zero-dependency MCP stdio server."""

from __future__ import annotations

import io
import json
import unittest
from pathlib import Path

from tokendiet import __version__, audit_payload
from tokendiet.mcp_server import TOOLS, handle_message, serve_stdio

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


class TestMcpServer(unittest.TestCase):
    def test_initialize_and_ping(self) -> None:
        init_resp = handle_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-03-26", "clientInfo": {"name": "test", "version": "1.0"}},
            }
        )
        assert init_resp is not None
        self.assertEqual(init_resp["result"]["protocolVersion"], "2025-03-26")
        self.assertEqual(init_resp["result"]["serverInfo"]["version"], __version__)
        self.assertIsNone(handle_message({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        ping_resp = handle_message({"jsonrpc": "2.0", "id": 2, "method": "ping"})
        assert ping_resp is not None
        self.assertEqual(ping_resp["result"], {})

    def test_tools_list_and_self_audit_grade_a(self) -> None:
        resp = handle_message({"jsonrpc": "2.0", "id": 3, "method": "tools/list"})
        assert resp is not None
        tools = resp["result"]["tools"]
        names = [t["name"] for t in tools]
        self.assertEqual(
            names,
            ["audit_agent_context", "audit_mcp_schema", "estimate_context_cost", "minify_mcp_schema"],
        )
        # Practice what we preach: TokenDiet's own MCP schema must be prompt-cache safe and Grade A
        report = audit_payload({"tools": TOOLS}, source="tokendiet-mcp")
        self.assertTrue(report.prompt_cache_safe)
        self.assertGreaterEqual(report.score, 90)

    def test_all_four_tools_via_stdio(self) -> None:
        sample = json.loads((EXAMPLES_DIR / "bloated_mcp_tools.json").read_text(encoding="utf-8"))
        requests = [
            {"jsonrpc": "2.0", "id": 10, "method": "tools/call", "params": {"name": "audit_mcp_schema", "arguments": {"payload": sample, "model_id": "claude-sonnet"}}},
            {"jsonrpc": "2.0", "id": 11, "method": "tools/call", "params": {"name": "minify_mcp_schema", "arguments": {"payload": sample, "aggressive": True}}},
            {"jsonrpc": "2.0", "id": 12, "method": "tools/call", "params": {"name": "audit_agent_context", "arguments": {"text": "# AGENTS.md\nUpdated 2026-11-23T12:00:00Z\nKeep prompts short."}}},
            {"jsonrpc": "2.0", "id": 13, "method": "tools/call", "params": {"name": "estimate_context_cost", "arguments": {"tokens_per_turn": 5000, "turns_per_day": 150, "team_size": 3}}},
        ]
        stdin = io.StringIO("\n".join(json.dumps(r) for r in requests) + "\n")
        stdout = io.StringIO()
        serve_stdio(stdin=stdin, stdout=stdout)
        lines = [json.loads(ln) for ln in stdout.getvalue().strip().splitlines()]
        self.assertEqual(len(lines), 4)

        audit_res = lines[0]["result"]["structuredContent"]
        self.assertIn("score", audit_res)
        self.assertGreater(audit_res["total_tokens"], 0)

        min_res = lines[1]["result"]["structuredContent"]
        self.assertTrue(min_res["invariants_verified"])
        self.assertGreater(min_res["tokens_saved"], 0)

        ctx_res = lines[2]["result"]["structuredContent"]
        self.assertFalse(ctx_res["prompt_cache_safe"])

        cost_res = lines[3]["result"]["structuredContent"]
        self.assertIn("claude-sonnet", cost_res["models"])
        self.assertIn("gemini-2.5-pro", cost_res["models"])

    def test_unknown_tool_returns_invalid_params(self) -> None:
        resp = handle_message({"jsonrpc": "2.0", "id": 99, "method": "tools/call", "params": {"name": "nope", "arguments": {}}})
        assert resp is not None
        self.assertEqual(resp["error"]["code"], -32602)


if __name__ == "__main__":
    unittest.main()
