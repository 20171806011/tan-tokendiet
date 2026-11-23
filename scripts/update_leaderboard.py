#!/usr/bin/env python3
"""TAN TokenDiet — Live Public MCP Server Token Efficiency Leaderboard Updater.

Runs automatically on GitHub Actions (public repo = unlimited free minutes) to:
  1. Preserve exact empirical tool-schema audits from official modelcontextprotocol/servers (44 tools)
  2. Refresh live GitHub stars, last-push dates, and public repo context telemetry across major MCP servers
  3. Write docs/data/mcp_leaderboard.json and update docs/sitemap.xml lastmod timestamps
"""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "docs" / "data" / "mcp_leaderboard.json"
SITEMAP_PATH = ROOT / "docs" / "sitemap.xml"

# Empirically measured exact tool-schema audits from benchmarks/RESULTS.md (44 official tools)
OFFICIAL_MEASURED = [
    {
        "name": "mcp-server-filesystem",
        "repo": "modelcontextprotocol/servers",
        "path": "src/filesystem",
        "category": "Official Reference",
        "measurement_mode": "exact_schema_audit",
        "tools": 16,
        "raw_tokens": 2133,
        "safe_tokens": 1581,
        "safe_savings_pct": 25.9,
        "aggressive_tokens": 931,
        "aggressive_savings_pct": 56.4,
        "findings": 51,
        "invariants_passed": True,
    },
    {
        "name": "mcp-server-git",
        "repo": "modelcontextprotocol/servers",
        "path": "src/git",
        "category": "Official Reference",
        "measurement_mode": "exact_schema_audit",
        "tools": 14,
        "raw_tokens": 1805,
        "safe_tokens": 1170,
        "safe_savings_pct": 35.2,
        "aggressive_tokens": 1170,
        "aggressive_savings_pct": 35.2,
        "findings": 66,
        "invariants_passed": True,
    },
    {
        "name": "mcp-server-memory",
        "repo": "modelcontextprotocol/servers",
        "path": "src/memory",
        "category": "Official Reference",
        "measurement_mode": "exact_schema_audit",
        "tools": 9,
        "raw_tokens": 1014,
        "safe_tokens": 704,
        "safe_savings_pct": 30.6,
        "aggressive_tokens": 411,
        "aggressive_savings_pct": 59.5,
        "findings": 28,
        "invariants_passed": True,
    },
    {
        "name": "mcp-server-time",
        "repo": "modelcontextprotocol/servers",
        "path": "src/time",
        "category": "Official Reference",
        "measurement_mode": "exact_schema_audit",
        "tools": 3,
        "raw_tokens": 354,
        "safe_tokens": 213,
        "safe_savings_pct": 39.8,
        "aggressive_tokens": 213,
        "aggressive_savings_pct": 39.8,
        "findings": 17,
        "invariants_passed": True,
    },
    {
        "name": "mcp-server-sequentialthinking",
        "repo": "modelcontextprotocol/servers",
        "path": "src/sequentialthinking",
        "category": "Official Reference",
        "measurement_mode": "exact_schema_audit",
        "tools": 1,
        "raw_tokens": 294,
        "safe_tokens": 234,
        "safe_savings_pct": 20.4,
        "aggressive_tokens": 66,
        "aggressive_savings_pct": 77.6,
        "findings": 4,
        "invariants_passed": True,
    },
    {
        "name": "mcp-server-fetch",
        "repo": "modelcontextprotocol/servers",
        "path": "src/fetch",
        "category": "Official Reference",
        "measurement_mode": "exact_schema_audit",
        "tools": 1,
        "raw_tokens": 257,
        "safe_tokens": 189,
        "safe_savings_pct": 26.5,
        "aggressive_tokens": 189,
        "aggressive_savings_pct": 26.5,
        "findings": 8,
        "invariants_passed": True,
    },
]

# Major public ecosystem MCP repositories tracked live via GitHub REST API
ECOSYSTEM_REPOS = [
    ("github/github-mcp-server", "Code Hosting & PRs"),
    ("microsoft/playwright-mcp", "Browser Automation"),
    ("upstash/context7", "Live Docs Retrieval"),
    ("cloudflare/mcp-server-cloudflare", "Cloud Infrastructure"),
    ("stripe/agent-toolkit", "Payments & Billing"),
    ("makenotion/notion-mcp-server", "Knowledge Base"),
    ("supabase-community/supabase-mcp", "Database & Auth"),
    ("firecrawl/firecrawl-mcp-server", "Web Scraping"),
]


def gh_get(url: str) -> Dict[str, Any]:
    hdrs = {"Accept": "application/vnd.github+json", "User-Agent": "tan-tokendiet-leaderboard/1.3"}
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    if tok:
        hdrs["Authorization"] = f"Bearer {tok}"
    req = urllib.request.Request(url, headers=hdrs)
    with urllib.request.urlopen(req, timeout=12) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Fetch live star/push telemetry for modelcontextprotocol/servers once
    official_meta: Dict[str, Any] = {}
    try:
        m = gh_get("https://api.github.com/repos/modelcontextprotocol/servers")
        official_meta = {
            "stars": m.get("stargazers_count", 0),
            "pushed_at": m.get("pushed_at"),
            "html_url": m.get("html_url", "https://github.com/modelcontextprotocol/servers"),
        }
    except Exception:
        official_meta = {"stars": 0, "pushed_at": None, "html_url": "https://github.com/modelcontextprotocol/servers"}

    measured_rows: List[Dict[str, Any]] = []
    for row in OFFICIAL_MEASURED:
        # Monthly cost on Claude Sonnet 4.x ($3/1M uncached, $6/1M 1h cache write miss) @ 10 devs x 200 turns/day (60k turns/mo)
        monthly_uncached_usd = round((row["raw_tokens"] * 60_000 / 1_000_000.0) * 3.0, 2)
        monthly_safe_usd = round((row["safe_tokens"] * 60_000 / 1_000_000.0) * 3.0, 2)
        monthly_1h_broken_usd = round(monthly_uncached_usd * 2.0, 2)
        measured_rows.append(
            {
                **row,
                "repo_stars": official_meta["stars"],
                "repo_pushed_at": official_meta["pushed_at"],
                "repo_url": f"https://github.com/{row['repo']}/tree/main/{row['path']}",
                "monthly_uncached_usd_10dev": monthly_uncached_usd,
                "monthly_safe_usd_10dev": monthly_safe_usd,
                "monthly_1h_miss_usd_10dev": monthly_1h_broken_usd,
            }
        )

    ecosystem_rows: List[Dict[str, Any]] = []
    for repo_full, category in ECOSYSTEM_REPOS:
        try:
            rm = gh_get(f"https://api.github.com/repos/{repo_full}")
            readme_bytes = 0
            try:
                rd = gh_get(f"https://api.github.com/repos/{repo_full}/readme")
                readme_bytes = int(rd.get("size", 0))
            except Exception:
                pass
            ecosystem_rows.append(
                {
                    "name": repo_full.split("/")[1],
                    "repo": repo_full,
                    "repo_url": rm.get("html_url", f"https://github.com/{repo_full}"),
                    "category": category,
                    "language": rm.get("language") or "Mixed",
                    "stars": rm.get("stargazers_count", 0),
                    "forks": rm.get("forks_count", 0),
                    "open_issues": rm.get("open_issues_count", 0),
                    "pushed_at": rm.get("pushed_at"),
                    "readme_bytes": readme_bytes,
                    "est_doc_tokens": max(1, round(readme_bytes / 3.8)),
                    "description": (rm.get("description") or "")[:140],
                }
            )
        except Exception:
            continue

    ecosystem_rows.sort(key=lambda x: -int(x.get("stars", 0)))

    payload = {
        "schema_version": "1.3.0",
        "generated_at_utc": now_iso,
        "benchmark_assumptions": {
            "model": "Claude Sonnet 4.x ($3.00/1M input, $0.30/1M cached read, 2.0x 1h cache write)",
            "team_profile": "10 developers x 200 turns/day x 30 days = 60,000 turns/month",
        },
        "summary": {
            "official_servers_audited": len(measured_rows),
            "official_tools_audited": sum(r["tools"] for r in measured_rows),
            "combined_raw_tokens": 5840,
            "combined_safe_tokens": 4074,
            "combined_safe_savings_pct": 30.2,
            "combined_aggressive_tokens": 2962,
            "combined_aggressive_savings_pct": 49.3,
            "ecosystem_repos_tracked": len(ecosystem_rows),
        },
        "official_measured": measured_rows,
        "ecosystem_watchlist": ecosystem_rows,
    }

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://20171806011.github.io/tan-tokendiet/</loc>
    <lastmod>{today_str}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://20171806011.github.io/tan-tokendiet/leaderboard.html</loc>
    <lastmod>{today_str}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://20171806011.github.io/tan-tokendiet/cache-calculator.html</loc>
    <lastmod>{today_str}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>
</urlset>
"""
    SITEMAP_PATH.write_text(sitemap_xml, encoding="utf-8")
    print(f"Updated {DATA_PATH} ({len(measured_rows)} exact + {len(ecosystem_rows)} live ecosystem repos) and {SITEMAP_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
