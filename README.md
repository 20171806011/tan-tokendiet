# TAN TokenDiet

**Audit, benchmark, and safely compact MCP tool schemas & AI agent context files to cut LLM token burn and fix prompt-cache misses.**

- **Live Browser Analyzer (100% client-side, zero upload):** https://20171806011.github.io/tan-tokendiet/
- **Zero-dependency Python CLI:** works on Python 3.9+ with zero third-party packages.

---

## Why TokenDiet?

Connecting 5–15 MCP servers (`mcp.json`, `tools/list`) alongside `AGENTS.md`, `CLAUDE.md`, `SKILL.md`, and `.cursorrules` quietly injects **5,000–40,000 static tokens into every single agent turn**:

1. **Pydantic / Zod Schema Overhead:** redundant `$schema`, `additionalProperties: false`, empty `required: []`, and auto-generated `title` annotations duplicating every field name.
2. **Inline Code Examples & Boilerplate:** multi-paragraph tool descriptions and repeated policy text re-sent hundreds of times per day.
3. **Broken KV Prompt Caches:** ISO timestamps, `{{now}}` / `{{uuid}}` templates, or unsorted tool/property keys silently bust Anthropic/OpenAI/Gemini prefix caching — costing 4x–10x more per input token.

On a real 4-tool sample schema (`examples/bloated_mcp_tools.json`), `tokendiet minify --aggressive` cuts token overhead by **41.3%** (`884 → 519 tokens`) while **verifying 100% JSON Schema structural invariants** and fixing KV prompt-cache safety (`NO → YES`).

---

## Quick Start (CLI)

```bash
pip install git+https://github.com/20171806011/tan-tokendiet.git
```

Or run directly from source without installing:

```bash
# Audit an MCP tools/list JSON, mcp.json, AGENTS.md, or an entire repository
python3 -m tokendiet audit examples/bloated_mcp_tools.json --model claude-sonnet --turns-per-day 200 --team-size 5

# Safely compact an MCP / OpenAI / Anthropic tool schema with structural invariant verification
python3 -m tokendiet minify examples/bloated_mcp_tools.json --aggressive -o tools.compact.json

# CI regression gate: fail build if a PR adds >200 tokens to tool/agent context
python3 -m tokendiet diff tools.compact.json examples/bloated_mcp_tools.json --max-delta 200
```

## 12 Diagnostic Rules

| Rule | Severity | What It Detects |
|---|---|---|
| `TD001` | Warning / Critical | Oversized tool description (`>120` tokens) |
| `TD002` | Warning | Oversized parameter description (`>50` tokens) |
| `TD003` | Info | Redundant `$schema`, `additionalProperties: false`, empty `required: []`, duplicate Pydantic/Zod `title` |
| `TD004` | Warning / Critical | Excessive per-turn static context (`>4,000` / `>12,000` tokens) or `8+` always-on MCP servers |
| `TD005` | Critical | Prompt-cache-busting timestamps, `{{now}}`, `Date.now()`, or UUID literals in static prefix |
| `TD006` | Info / Warning | Unsorted tools array or property keys causing non-deterministic KV prefix misses |
| `TD007` | Warning | Repeated boilerplate sentences across `>=3` tools or duplicated instruction lines |
| `TD008` | Info / Warning | Fenced code blocks or inline examples embedded inside always-loaded descriptions |
| `TD009` | Warning | Deeply nested inline JSON schema (`depth >= 5`) |
| `TD010` | Warning | Large inline `enum` list (`>=15` values) re-sent every turn |
| `TD011` | Critical | Duplicate tool names registered across servers |
| `TD012` | Info | Excessive whitespace padding in agent instruction files |

---

## TAN TokenDiet Pro (£15 GBP / $19 USD — One-Time Team License)

The core CLI and browser analyzer are open-source (MIT). For engineering teams automating context governance in CI/CD, **TAN TokenDiet Pro** adds:

- **GitHub Actions PR Token Budget Gate** (automated PR comments with exact token & monthly USD/GBP delta + CI failure thresholds)
- **Multi-Repo FinOps Batch Auditor** (standalone HTML Executive Report + CSV export across an org's repos)
- **Curated MCP Compaction Presets** (GitHub, PostgreSQL, Playwright, Linear, Slack stacks)
- **Perpetual Commercial v1.x License** with 14-day refund guarantee

See details & licensing at: https://20171806011.github.io/tan-tokendiet/#pricing

## Running Tests

```bash
python3 -m unittest discover -s tests -v
```

## License

Core CLI & browser analyzer: [MIT License](LICENSE).
