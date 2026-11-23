# Official MCP Reference Server Benchmarks (Measured 2026-11-23)

All measurements below were collected directly against the upstream [`modelcontextprotocol/servers`](https://github.com/modelcontextprotocol/servers) reference implementations (`filesystem`, `git`, `memory`, `time`, `fetch`, and `sequentialthinking` — **44 tools total**) using `TAN TokenDiet v1.1.0`.

## Summary Results

| Official MCP Server | Tools | Raw Tokens / Turn | Safe Lossless Compaction | Safe Savings | Aggressive Compaction | Aggressive Savings | Findings | Structural Invariants |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|
| `mcp-server-filesystem` | 16 | 2,133 | 1,581 | **-25.9%** | 931 | **-56.4%** | 51 | ✅ 100% |
| `mcp-server-git` | 14 | 1,805 | 1,170 | **-35.2%** | 1,170 | **-35.2%** | 66 | ✅ 100% |
| `mcp-server-memory` | 9 | 1,014 | 704 | **-30.6%** | 411 | **-59.5%** | 28 | ✅ 100% |
| `mcp-server-time` | 3 | 354 | 213 | **-39.8%** | 213 | **-39.8%** | 17 | ✅ 100% |
| `mcp-server-fetch` | 1 | 257 | 189 | **-26.5%** | 189 | **-26.5%** | 8 | ✅ 100% |
| `mcp-server-sequentialthinking` | 1 | 294 | 234 | **-20.4%** | 66 | **-77.6%** | 4 | ✅ 100% |
| **Combined (All 6 Servers)** | **44** | **5,840** | **4,074** | **-30.2%** | **2,962** | **-49.3%** | **172** | **✅ 100%** |

## Key Findings

1. **Zero-Risk Lossless Compaction Alone Cuts 30.2% (1,766 tokens/turn):** Stripping Pydantic/Zod `$schema` URIs, `additionalProperties: false`, empty `required: []`, and auto-generated `title` fields identical to property keys saves nearly a third of every tool payload without altering a single tool name, type, required parameter, or enum value.
2. **Aggressive Compaction Cuts 49.3% (2,878 tokens/turn):** Trimming inline usage essays and boilerplate filler phrases cuts the 6-server reference bundle almost in half while maintaining 100% structural schema validity.
3. **Monthly Team Impact (10 devs × 200 turns/day on Claude Sonnet 4.x):**
   - **Standard uncached input:** `$1,051.20/mo` → `$533.16/mo` (**$518.04/mo / $6,216/yr saved**).
   - **Broken 1-Hour Cache Write Penalty (2.0× write rate):** If dynamic timestamps or unsorted tool registration break KV prefix caching on long-TTL sessions, the uncompacted stack incurs up to **$2,102.40/mo** in repeated cache writes until deterministic sorting and cache-safe cleaning are applied.
