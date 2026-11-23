# TAN TokenDiet v1.4.0

<!-- mcp-name: io.github.20171806011/tan-tokendiet -->

**Audit, benchmark, and safely compact MCP tool schemas & AI agent context files to cut LLM token burn and fix 5m / 1h prompt-cache misses.**

- **Live Browser Analyzer (100% client-side, zero upload):** https://20171806011.github.io/tan-tokendiet/
- **Zero-dependency Python CLI & MCP Stdio Server:** `tokendiet` CLI + `tokendiet-mcp` (`docker run -i --rm ghcr.io/20171806011/tan-tokendiet:1.4.0`)
- **Reusable GitHub Action:** `uses: 20171806011/tan-tokendiet@v1.4.0`

---

## Verified Empirical Benchmarks (`modelcontextprotocol/servers`, 44 Tools)

Measured directly against upstream official MCP reference servers ([full methodology](benchmarks/RESULTS.md)):

| Official MCP Server | Tools | Raw Tok/Turn | Safe Lossless | Aggressive | Structural Invariants |
|---|---:|---:|---:|---:|:---:|
| `mcp-server-filesystem` | 16 | 2,133 | 1,581 (**-25.9%**) | 931 (**-56.4%**) | ✅ 100% |
| `mcp-server-git` | 14 | 1,805 | 1,170 (**-35.2%**) | 1,170 (**-35.2%**) | ✅ 100% |
| `mcp-server-memory` | 9 | 1,014 | 704 (**-30.6%**) | 411 (**-59.5%**) | ✅ 100% |
| `mcp-server-time` | 3 | 354 | 213 (**-39.8%**) | 213 (**-39.8%**) | ✅ 100% |
| `mcp-server-fetch` | 1 | 257 | 189 (**-26.5%**) | 189 (**-26.5%**) | ✅ 100% |
| `mcp-server-sequentialthinking` | 1 | 294 | 234 (**-20.4%**) | 66 (**-77.6%**) | ✅ 100% |
| **Combined 6-Server Stack** | **44** | **5,840** | **4,074 (-30.2%)** | **2,962 (-49.3%)** | **✅ All 44 Passed** |

> **Why Prompt-Cache Safety Matters More Than Raw Token Count:** Recent coding agents (e.g. Claude Code) write 1-hour TTL prompt caches billed at **2.0× input** (vs 1.25× for 5-minute TTL). A single dynamic timestamp, UUID, or non-deterministic tool order silently turns a 90% cached-read discount into repeated 2.0× cache writes. TokenDiet flags all cache-busters (`TD005` / `TD006`) and enforces deterministic JSON sorting.

---

## Quick Start (CLI & GitHub Action)

### CLI
```bash
pip install git+https://github.com/20171806011/tan-tokendiet.git

# Audit an MCP schema JSON, mcp.json, AGENTS.md, or an entire repository
tokendiet audit examples/bloated_mcp_tools.json --model claude-sonnet --turns-per-day 200 --team-size 5

# Safely compact tool schemas with 100% JSON Schema structural invariant verification
tokendiet minify examples/bloated_mcp_tools.json --aggressive -o tools.compact.json

# CI regression diff gate
tokendiet diff tools.compact.json examples/bloated_mcp_tools.json --max-delta 200
```

### Reusable GitHub Action
```yaml
- uses: 20171806011/tan-tokendiet@v1.4.0
  with:
    path: "."
    model: "claude-sonnet"
    max-tokens: "4000"
    fail-on-cache-buster: "true"
```

---

## Instant Agent-to-Agent Services (CROO Network · Base USDC)

Using **Claude Code**, **Codex**, or any **CROO Skill** agent? Hire our live 24/7 deterministic Base Mainnet USDC endpoints directly via [CROO Network](https://agent.croo.network):

| Agent (`agentId`) | Service | Price (Base USDC) | SLA |
|---|---|---:|---:|
| **TAN TokenDiet Optimizer** (`bdd0a112-9a6a-4e77-80b8-71841f4426de`) | Quick Token Counter, Compress & JSON Minifier | **$0.01** | 5m |
| **TAN TokenDiet Optimizer** (`bdd0a112-9a6a-4e77-80b8-71841f4426de`) | Prompt & Context Token Audit | **$0.05** | 10m |
| **TAN TokenDiet Optimizer** (`bdd0a112-9a6a-4e77-80b8-71841f4426de`) | GitHub Repo Context Footprint Audit | **$0.25** | 15m |
| **TAN CodeGuard Scanner** (`b4b4e321-cbd4-4497-b0a6-4789ce6b88dd`) | Validate JSON, Schema & Code Syntax / Security Scan | **$0.01–$0.20** | 5–15m |
| **TAN ChainCheck Verifier** (`45a14835-309a-4f6e-90d1-ab03c9191ef5`) | Verify Live Base & ETH Price, Gas, TVL, Wallet & x402 Audit | **$0.01–$0.05** | 5–10m |

---

## Commercial Editions (Zero Subscriptions)

- **TAN TokenDiet Free (£0 · MIT):** Core CLI, 100% client-side browser analyzer, MCP Stdio Server (`io.github.20171806011/tan-tokendiet`), reusable GitHub Action, 12 rules.
- **TAN TokenDiet Pro Kit (£15 GBP / $19 USD · one-time):** Automated GitHub PR Cost-Delta Commenter & Budget Gate, Multi-Repo FinOps Batch Auditor (HTML Executive Report + CSV), curated MCP server profile presets, perpetual commercial v1.x team license.
- **Done-For-You MCP & Prompt-Cache Audit (£29 GBP / $39 USD · fixed fee, 24h):** Hands-on audit of your repo/MCP stack, drop-in compacted schemas + cache-fix PR, Executive FinOps report, **includes TokenDiet Pro Kit**.

Details, live interactive calculator & policies: https://20171806011.github.io/tan-tokendiet/

## License

Core CLI, Action & browser analyzer: [MIT License](LICENSE).
