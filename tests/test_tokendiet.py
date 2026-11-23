"""Comprehensive unit & CLI integration tests for TAN TokenDiet."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tokendiet.analyzer import audit_path, audit_payload, audit_text
from tokendiet.cli import main as cli_main
from tokendiet.minifier import minify_tools_payload
from tokendiet.pricing import estimate_monthly_cost
from tokendiet.tokenizer import count_tokens

EXAMPLE_MCP = Path(__file__).resolve().parent.parent / "examples" / "bloated_mcp_tools.json"


class TestTokenizer(unittest.TestCase):
    def test_empty_and_basic_strings(self) -> None:
        self.assertEqual(count_tokens(""), 0)
        self.assertGreater(count_tokens("hello world"), 0)
        self.assertGreater(count_tokens("camelCaseIdentifierName"), 2)

    def test_cjk_handling(self) -> None:
        toks = count_tokens("自动化审计工具用于降低大模型输入成本")
        self.assertGreaterEqual(toks, 18)

    def test_json_proportionality(self) -> None:
        small = count_tokens('{"a":1}')
        large = count_tokens(json.dumps({"items": [{"id": i, "name": f"item_{i}"} for i in range(50)]}))
        self.assertGreater(large, small * 20)


class TestPricing(unittest.TestCase):
    def test_cache_discount_reduces_cost(self) -> None:
        no_cache = estimate_monthly_cost(10_000, turns_per_day=100, team_size=5, model_id="claude-sonnet", cache_hit_rate=0.0)
        with_cache = estimate_monthly_cost(10_000, turns_per_day=100, team_size=5, model_id="claude-sonnet", cache_hit_rate=0.8)
        self.assertGreater(no_cache["effective_monthly_usd"], with_cache["effective_monthly_usd"])
        self.assertGreater(with_cache["cache_savings_usd"], 0)
        self.assertGreater(no_cache["effective_monthly_gbp"], 0)


class TestAnalyzerAndMinifier(unittest.TestCase):
    def test_example_mcp_detects_key_antipatterns(self) -> None:
        payload = json.loads(EXAMPLE_MCP.read_text(encoding="utf-8"))
        report = audit_payload(payload, source="examples/bloated_mcp_tools.json")
        rule_ids = {f.rule_id for f in report.findings}
        self.assertEqual(report.kind, "mcp_tools")
        self.assertEqual(report.tool_count, 4)
        self.assertFalse(report.prompt_cache_safe)
        self.assertIn("TD003", rule_ids)  # $schema / additionalProperties / redundant title / empty required
        self.assertIn("TD005", rule_ids)  # ISO timestamp cache buster
        self.assertIn("TD006", rule_ids)  # unsorted tools & keys
        self.assertIn("TD007", rule_ids)  # repeated boilerplate across >=3 tools
        self.assertIn("TD008", rule_ids)  # fenced code examples in descriptions
        self.assertIn("TD010", rule_ids)  # large enum (16 values)
        self.assertGreater(report.estimated_reducible_tokens, 50)

    def test_minifier_preserves_schema_invariants_and_saves_tokens(self) -> None:
        payload = json.loads(EXAMPLE_MCP.read_text(encoding="utf-8"))
        safe_res = minify_tools_payload(payload, aggressive=False)
        agg_res = minify_tools_payload(payload, aggressive=True)
        self.assertTrue(safe_res.invariants_verified)
        self.assertTrue(agg_res.invariants_verified)
        self.assertGreater(safe_res.tokens_saved, 0)
        self.assertGreater(agg_res.tokens_saved, safe_res.tokens_saved)
        # Verify tools are deterministically sorted
        names = [t["name"] for t in agg_res.minified_payload["tools"]]
        self.assertEqual(names, sorted(names))
        # Verify $schema and redundant additionalProperties stripped
        for t in agg_res.minified_payload["tools"]:
            self.assertNotIn("$schema", t["inputSchema"])
            self.assertNotIn("additionalProperties", t["inputSchema"])

    def test_mcp_config_detection(self) -> None:
        cfg = {
            "mcpServers": {
                f"srv_{i}": {"command": "npx", "args": ["-y", f"@org/mcp-{i}"]}
                for i in range(9)
            }
        }
        rep = audit_payload(cfg, source="mcp.json")
        self.assertEqual(rep.kind, "mcp_config")
        self.assertEqual(rep.tool_count, 9)
        self.assertTrue(any(f.rule_id == "TD004" and f.severity == "critical" for f in rep.findings))

    def test_instruction_file_cache_buster(self) -> None:
        md = "# AGENTS.md\nCurrent timestamp: {{now}}\nRun tests before commit.\n"
        rep = audit_text(md, source="AGENTS.md")
        self.assertEqual(rep.kind, "agent_instructions")
        self.assertFalse(rep.prompt_cache_safe)
        self.assertTrue(any(f.rule_id == "TD005" for f in rep.findings))

    def test_directory_recursive_audit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "AGENTS.md").write_text("# Instructions\nKeep diffs minimal.\n", encoding="utf-8")
            (root / "tools.json").write_text(EXAMPLE_MCP.read_text(encoding="utf-8"), encoding="utf-8")
            rep = audit_path(root)
            self.assertEqual(rep.kind, "directory")
            self.assertEqual(len(rep.files_scanned), 2)
            self.assertEqual(rep.tool_count, 4)


class TestCLI(unittest.TestCase):
    def test_cli_audit_budget_and_cache_gates(self) -> None:
        rc_ok = cli_main(["audit", str(EXAMPLE_MCP), "--json"])
        self.assertEqual(rc_ok, 0)
        rc_budget = cli_main(["audit", str(EXAMPLE_MCP), "--max-tokens", "50", "--json"])
        self.assertEqual(rc_budget, 2)
        rc_cache = cli_main(["audit", str(EXAMPLE_MCP), "--fail-on-cache-buster", "--json"])
        self.assertEqual(rc_cache, 3)

    def test_cli_minify_and_diff(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_path = Path(td) / "compact.json"
            rc = cli_main(["minify", str(EXAMPLE_MCP), "--aggressive", "-o", str(out_path)])
            self.assertEqual(rc, 0)
            self.assertTrue(out_path.exists())
            # Diff from compact -> bloated exceeds +20 tokens -> exits 2
            rc_fail = cli_main(["diff", str(out_path), str(EXAMPLE_MCP), "--max-delta", "20"])
            self.assertEqual(rc_fail, 2)
            # Diff from bloated -> compact is negative -> passes with 0
            rc_pass = cli_main(["diff", str(EXAMPLE_MCP), str(out_path), "--max-delta", "0"])
            self.assertEqual(rc_pass, 0)


if __name__ == "__main__":
    unittest.main()
