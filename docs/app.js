/* TAN TokenDiet — 100% Client-Side Analyzer, Cost Modeler & Safe Schema Compactor */
(() => {
  "use strict";

  const USD_TO_GBP = 0.79;
  const MODELS = {
    "claude-sonnet": { name: "Claude Sonnet 4.x", input: 3.0, cached: 0.3, w5m: 1.25, w1h: 2.0 },
    "claude-opus": { name: "Claude Opus 4.x", input: 15.0, cached: 1.5, w5m: 1.25, w1h: 2.0 },
    "gpt-5": { name: "GPT-5 Flagship", input: 2.5, cached: 0.25, w5m: 1.0, w1h: 1.0 },
    "gemini-2.5-pro": { name: "Gemini 2.5 Pro", input: 1.25, cached: 0.31, w5m: 1.0, w1h: 1.0 },
    "gpt-4.1-mini": { name: "GPT-4.1 Mini", input: 0.4, cached: 0.1, w5m: 1.0, w1h: 1.0 },
    "gemini-2.5-flash": { name: "Gemini 2.5 Flash", input: 0.3, cached: 0.075, w5m: 1.0, w1h: 1.0 },
  };

  const SAMPLES = {
    mcp: JSON.stringify(
      {
        tools: [
          {
            name: "github_search_issues",
            description:
              "This tool allows you to search GitHub issues and pull requests across public and private repositories. Please note that you should always verify pagination limits before calling this tool in a loop. Always return structured JSON responses with citations to the exact issue URL.\n\nExample:\n```json\n{\"query\": \"is:open label:bug\", \"repo\": \"org/app\", \"per_page\": 20}\n```\nGenerated at 2026-11-23T05:00:00Z.",
            inputSchema: {
              $schema: "https://json-schema.org/draft/2020-12/schema",
              type: "object",
              additionalProperties: false,
              properties: {
                repo: {
                  type: "string",
                  title: "Repo",
                  description:
                    "The full repository name in owner/repo format. For example: {\"repo\": \"facebook/react\"}. Make sure that you include both the organization owner and the repository slug separated by a forward slash.",
                },
                query: {
                  type: "string",
                  title: "Query",
                  description:
                    "GitHub search query string supporting standard qualifiers such as is:open, label:, author:, and created:>YYYY-MM-DD.",
                },
                sort: {
                  type: "string",
                  title: "Sort",
                  enum: [
                    "created", "updated", "comments", "reactions", "reactions-+1",
                    "reactions--1", "reactions-smile", "reactions-thinking_face",
                    "reactions-heart", "reactions-tada", "interactions", "best-match",
                    "relevance", "asc", "desc", "priority",
                  ],
                },
              },
              required: ["query"],
            },
          },
          {
            name: "analytics_run_sql",
            description:
              "Use this tool whenever you need to execute a read-only SQL query against the analytics warehouse. Always return structured JSON responses with citations to the exact issue URL. Please note that destructive DDL or DML statements are blocked at the database proxy layer.\n\nExample:\n```sql\nSELECT date_trunc('day', created_at), count(*) FROM events GROUP BY 1 LIMIT 50;\n```",
            inputSchema: {
              $schema: "https://json-schema.org/draft/2020-12/schema",
              type: "object",
              additionalProperties: false,
              properties: {
                sql: {
                  type: "string",
                  title: "Sql",
                  description:
                    "A valid PostgreSQL SELECT statement to run against the read replica. Make sure that you include a LIMIT clause in order to prevent excessive memory usage on large event tables.",
                },
                timeout_ms: {
                  type: "integer",
                  title: "Timeout Ms",
                  description: "Maximum execution time in milliseconds.",
                },
              },
              required: ["sql"],
            },
          },
          {
            name: "slack_post_message",
            description:
              "This tool allows the agent to send a formatted Slack message into a channel or thread. Always return structured JSON responses with citations to the exact issue URL. Please note that posting to #general or #announcements requires explicit human approval.",
            inputSchema: {
              $schema: "https://json-schema.org/draft/2020-12/schema",
              type: "object",
              additionalProperties: false,
              properties: {
                text: {
                  type: "string",
                  title: "Text",
                  description: "The message body formatted in Slack mrkdwn syntax.",
                },
                channel: {
                  type: "string",
                  title: "Channel",
                  description: "Target Slack channel ID or channel name.",
                },
              },
              required: ["channel", "text"],
            },
          },
          {
            name: "deploy_preview_env",
            description:
              "Use this tool when you want to provision an ephemeral staging preview environment for a Git branch. Always return structured JSON responses with citations to the exact issue URL.",
            inputSchema: {
              $schema: "https://json-schema.org/draft/2020-12/schema",
              type: "object",
              additionalProperties: false,
              properties: {
                branch: {
                  type: "string",
                  title: "Branch",
                  description: "Git branch name to deploy.",
                },
              },
              required: [],
            },
          },
        ],
      },
      null,
      2
    ),
    agents: `# AGENTS.md — Engineering Rules\n\nGenerated timestamp: 2026-11-23T05:12:00Z | Session token: {{uuid}}\n\n## Core Workflow\nAlways run the complete unit test suite before creating any pull request or committing changes.\nAlways run the complete unit test suite before creating any pull request or committing changes.\n\n## API Boilerplate Example\n\`\`\`typescript\nexport async function fetchPaginatedRecords<T>(endpoint: string, pageSize = 50): Promise<T[]> {\n  const results: T[] = [];\n  let cursor: string | null = null;\n  do {\n    const url = cursor ? \`\${endpoint}?cursor=\${cursor}&limit=\${pageSize}\` : \`\${endpoint}?limit=\${pageSize}\`;\n    const response = await fetch(url, { headers: { Accept: "application/json" } });\n    if (!response.ok) throw new Error(\`Request failed with status \${response.status}\`);\n    const payload = await response.json();\n    results.push(...payload.items);\n    cursor = payload.nextCursor ?? null;\n  } while (cursor);\n  return results;\n}\n\`\`\`\n\n\n\n## Deployment Checklist\n1. Verify database migrations are backwards-compatible.\n2. Confirm zero TypeScript errors and zero lint regressions.\n3. Check feature flags before promoting to production.\n`,
    config: JSON.stringify(
      {
        mcpServers: {
          github: { command: "npx", args: ["-y", "@modelcontextprotocol/server-github"] },
          postgres: { command: "npx", args: ["-y", "@modelcontextprotocol/server-postgres"] },
          playwright: { command: "npx", args: ["-y", "@playwright/mcp@latest"] },
          slack: { command: "npx", args: ["-y", "@modelcontextprotocol/server-slack"] },
          linear: { command: "npx", args: ["-y", "@linear/mcp-server"] },
          notion: { command: "npx", args: ["-y", "@notionhq/notion-mcp-server"] },
          sentry: { command: "npx", args: ["-y", "@sentry/mcp-server"] },
          stripe: { command: "npx", args: ["-y", "@stripe/mcp"] },
        },
      },
      null,
      2
    ),
  };

  /* --- Calibrated zero-dependency BPE token estimator --- */
  const TOKEN_RE = /[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]|[A-Za-z]+|\d{1,3}|\s+|[^\sA-Za-z0-9\u4e00-\u9fff]+/g;
  const CAMEL_RE = /[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)|\d+/g;

  function countTokens(text) {
    if (!text) return 0;
    let total = 0;
    const matches = text.match(TOKEN_RE);
    if (!matches) return 0;
    for (const piece of matches) {
      const code = piece.charCodeAt(0);
      if (
        (code >= 0x4e00 && code <= 0x9fff) ||
        (code >= 0x3040 && code <= 0x30ff) ||
        (code >= 0xac00 && code <= 0xd7af)
      ) {
        total += 1.25;
      } else if (/^\s+$/.test(piece)) {
        const nl = (piece.match(/\n/g) || []).length;
        if (nl > 0) {
          total += nl * 0.85;
          const sp = piece.length - nl;
          if (sp >= 4) total += Math.ceil(sp / 4) * 0.4;
        } else if (piece.length > 1) {
          total += Math.ceil(piece.length / 4) * 0.5;
        }
      } else if (/^[A-Za-z]+$/.test(piece)) {
        const parts = piece.match(CAMEL_RE) || [piece];
        if (parts.length > 1) {
          for (const p of parts) {
            total += p.length <= 7 ? 1 : Math.ceil(p.length / 4.5);
          }
        } else if (piece.length <= 6) {
          total += 1;
        } else if (piece.length <= 12) {
          total += 1.35;
        } else {
          total += Math.ceil(piece.length / 4.2);
        }
      } else if (/^\d+$/.test(piece)) {
        total += 1;
      } else {
        total += piece.length <= 2 ? 0.85 : Math.ceil(piece.length / 2) * 0.85;
      }
    }
    return Math.max(1, Math.round(total));
  }

  function countJsonTokens(obj) {
    return countTokens(JSON.stringify(obj));
  }

  function schemaDepth(obj, cur = 0) {
    if (Array.isArray(obj)) {
      return obj.length ? Math.max(...obj.map((v) => schemaDepth(v, cur))) : cur;
    }
    if (obj && typeof obj === "object") {
      const vals = Object.values(obj);
      return vals.length ? Math.max(...vals.map((v) => schemaDepth(v, cur + 1))) : cur;
    }
    return cur;
  }

  const CACHE_BUSTERS = [
    ["ISO timestamp/date", /\b20\d{2}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?)?\b/g],
    ["Dynamic template variable", /\{\{\s*(?:now|date|time|timestamp|today|current_date|uuid|random)\b[^}]*\}\}/gi],
    ["Runtime clock/UUID call", /\b(?:Date\.now\(\)|new Date\(\)|datetime\.now\(\)|uuid4\(\))\b/g],
    ["UUID v4 literal", /\b[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b/gi],
  ];
  const EXAMPLE_RE = /(```|example\s*:|for example|e\.g\.,?\s*\{|<example>)/i;

  function extractTools(payload) {
    let raw = null;
    if (Array.isArray(payload) && payload.length && payload.every((x) => x && typeof x === "object")) {
      if (payload.some((x) => "name" in x || "function" in x || "functionDeclarations" in x)) raw = payload;
    } else if (payload && typeof payload === "object") {
      if (Array.isArray(payload.tools)) raw = payload.tools;
      else if (payload.result && Array.isArray(payload.result.tools)) raw = payload.result.tools;
      else if (Array.isArray(payload.functionDeclarations)) raw = payload.functionDeclarations;
    }
    if (!raw) return null;
    const norm = [];
    for (const item of raw) {
      if (item.function && typeof item.function === "object") {
        norm.push({
          name: String(item.function.name || "unnamed"),
          description: String(item.function.description || ""),
          inputSchema: item.function.parameters || {},
          _raw: item,
        });
      } else {
        norm.push({
          name: String(item.name || "unnamed"),
          description: String(item.description || ""),
          inputSchema: item.inputSchema || item.input_schema || item.parameters || {},
          _raw: item,
        });
      }
    }
    return norm;
  }

  function walkProperties(schema, toolName, findings, prefix = "") {
    if (!schema || typeof schema !== "object") return { params: 0, wasted: 0 };
    let params = 0;
    let wasted = 0;

    if (schema.additionalProperties === false) {
      wasted += 4;
      findings.push({
        rule_id: "TD003",
        severity: "info",
        target: `${toolName}${prefix}`,
        message: "Redundant `additionalProperties: false` adds tokens on every turn.",
        wasted: 4,
        suggestion: "Strip from model-facing schema and validate server-side.",
      });
    }
    if (Array.isArray(schema.required) && schema.required.length === 0) {
      wasted += 4;
      findings.push({
        rule_id: "TD003",
        severity: "info",
        target: `${toolName}${prefix}`,
        message: "Empty `required: []` array is redundant.",
        wasted: 4,
        suggestion: "Remove empty required arrays.",
      });
    }
    if ("$schema" in schema) {
      wasted += 12;
      findings.push({
        rule_id: "TD003",
        severity: "info",
        target: `${toolName}${prefix}`,
        message: "JSON Schema `$schema` URI is unnecessary in LLM tool payloads.",
        wasted: 12,
        suggestion: "Strip `$schema` metadata before registering tools.",
      });
    }
    if (Array.isArray(schema.enum) && schema.enum.length >= 15) {
      const et = countJsonTokens(schema.enum);
      const w = Math.round(et * 0.6);
      wasted += w;
      findings.push({
        rule_id: "TD010",
        severity: "warning",
        target: `${toolName}${prefix}`,
        message: `Large inline enum (${schema.enum.length} values, ~${et} tokens) sent every turn.`,
        wasted: w,
        suggestion: "Accept a validated string or expose valid values via an on-demand lookup.",
      });
    }

    if (schema.properties && typeof schema.properties === "object") {
      const keys = Object.keys(schema.properties);
      const sorted = [...keys].sort();
      if (keys.length >= 3 && keys.join("|") !== sorted.join("|")) {
        findings.push({
          rule_id: "TD006",
          severity: "info",
          target: `${toolName}${prefix}`,
          message: "Unsorted property keys can invalidate KV prompt caches.",
          wasted: 0,
          suggestion: "Sort property keys deterministically.",
        });
      }
      for (const [k, def] of Object.entries(schema.properties)) {
        params += 1;
        if (!def || typeof def !== "object") continue;
        if (typeof def.title === "string") {
          const nt = def.title.toLowerCase().replace(/[^a-z0-9]/g, "");
          const nk = k.toLowerCase().replace(/[^a-z0-9]/g, "");
          if (nt === nk) {
            const w = countTokens(def.title) + 3;
            wasted += w;
            findings.push({
              rule_id: "TD003",
              severity: "info",
              target: `${toolName}.${k}`,
              message: `Redundant \`title: "${def.title}"\` duplicates property key \`${k}\`.`,
              wasted: w,
              suggestion: "Strip auto-generated Pydantic/Zod title annotations.",
            });
          }
        }
        if (typeof def.description === "string") {
          const pt = countTokens(def.description);
          if (pt > 50) {
            const w = pt - 25;
            wasted += w;
            findings.push({
              rule_id: "TD002",
              severity: "warning",
              target: `${toolName}.${k}`,
              message: `Parameter description is ${pt} tokens (recommended <= 35).`,
              wasted: w,
              suggestion: "Condense to 1 concise sentence.",
            });
          }
          if (EXAMPLE_RE.test(def.description)) {
            const w = Math.max(8, Math.round(pt * 0.35));
            wasted += w;
            findings.push({
              rule_id: "TD008",
              severity: "info",
              target: `${toolName}.${k}`,
              message: "Inline example detected inside parameter description.",
              wasted: w,
              suggestion: "Move examples to docs unless strictly required for formatting.",
            });
          }
        }
        const sub = walkProperties(def, toolName, findings, `${prefix}.${k}`);
        params += sub.params;
        wasted += sub.wasted;
      }
    }
    if (schema.items && typeof schema.items === "object") {
      const sub = walkProperties(schema.items, toolName, findings, `${prefix}[]`);
      params += sub.params;
      wasted += sub.wasted;
    }
    return { params, wasted };
  }

  function scoreReport(totalTokens, findings, cacheSafe) {
    let score = 100;
    for (const f of findings) {
      if (f.severity === "critical") score -= 14;
      else if (f.severity === "warning") score -= 6;
      else score -= 2;
    }
    if (!cacheSafe) score -= 10;
    if (totalTokens > 12000) score -= 15;
    else if (totalTokens > 4000) score -= 6;
    score = Math.max(0, Math.min(100, score));
    const grade = score >= 90 ? "A" : score >= 78 ? "B" : score >= 62 ? "C" : score >= 45 ? "D" : "F";
    return { score, grade };
  }

  function auditText(text) {
    const trimmed = text.trim();
    if (!trimmed) {
      return {
        kind: "empty",
        totalTokens: 0,
        reducible: 0,
        score: 100,
        grade: "—",
        cacheSafe: true,
        tools: [],
        findings: [],
        parsedToolsPayload: null,
      };
    }

    if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
      try {
        const parsed = JSON.parse(trimmed);
        const tools = extractTools(parsed);
        if (tools) {
          const findings = [];
          const toolMetrics = [];
          let wasted = 0;
          let cacheSafe = true;
          const totalTokens = countJsonTokens(parsed);

          if (totalTokens > 12000) {
            findings.push({
              rule_id: "TD004",
              severity: "critical",
              target: "payload",
              message: `Tool schemas consume ~${totalTokens.toLocaleString()} tokens EVERY turn (>12,000 critical).`,
              wasted: Math.round(totalTokens * 0.3),
              suggestion: "Split MCP servers into task profiles and enable deferred tool loading.",
            });
          } else if (totalTokens > 4000) {
            findings.push({
              rule_id: "TD004",
              severity: "warning",
              target: "payload",
              message: `Tool schemas consume ~${totalTokens.toLocaleString()} tokens per turn (>4,000 warning).`,
              wasted: Math.round(totalTokens * 0.2),
              suggestion: "Compact verbose descriptions and strip auto-generated schema metadata.",
            });
          }

          const rawStr = JSON.stringify(parsed);
          for (const [label, pat] of CACHE_BUSTERS) {
            const hits = rawStr.match(pat);
            if (hits && hits.length) {
              cacheSafe = false;
              findings.push({
                rule_id: "TD005",
                severity: "critical",
                target: "payload",
                message: `Prompt-cache-busting ${label} found (${hits.length}x) inside static tool definitions.`,
                wasted: 0,
                suggestion: "Remove dynamic timestamps/UUIDs so provider KV caches unlock 75–90% discounts.",
              });
            }
          }

          const names = tools.map((t) => t.name);
          if (names.length >= 3 && names.join("|") !== [...names].sort().join("|")) {
            findings.push({
              rule_id: "TD006",
              severity: "warning",
              target: "tools[]",
              message: "Tools array is unsorted; dynamic registration order breaks KV prefix caching.",
              wasted: 0,
              suggestion: "Sort tools alphabetically with TokenDiet compactor.",
            });
          }

          const sentCounts = new Map();
          for (const t of tools) {
            const sents = t.description.split(/(?<=[.!?])\s+|\n+/);
            for (const s of sents) {
              const clean = s.trim();
              if (clean.length >= 35) sentCounts.set(clean, (sentCounts.get(clean) || 0) + 1);
            }
          }
          for (const [sent, cnt] of sentCounts.entries()) {
            if (cnt >= 3) {
              const w = countTokens(sent) * (cnt - 1);
              wasted += w;
              findings.push({
                rule_id: "TD007",
                severity: "warning",
                target: "shared",
                message: `Boilerplate repeated across ${cnt} tools (~${w} wasted tokens): "${sent.slice(0, 68)}..."`,
                wasted: w,
                suggestion: "Hoist shared policy once into system instructions instead of repeating per tool.",
              });
            }
          }

          for (const t of tools) {
            const dt = countTokens(t.description);
            const st = countJsonTokens(t.inputSchema);
            const tt = countJsonTokens(t._raw);
            const depth = schemaDepth(t.inputSchema);
            if (dt > 120) {
              const w = dt - 60;
              wasted += w;
              findings.push({
                rule_id: "TD001",
                severity: dt > 250 ? "critical" : "warning",
                target: t.name,
                message: `Tool description is ${dt} tokens (target <= 80).`,
                wasted: w,
                suggestion: "Keep description to 1–2 direct sentences.",
              });
            }
            if (EXAMPLE_RE.test(t.description)) {
              const w = Math.max(15, Math.round(dt * 0.35));
              wasted += w;
              findings.push({
                rule_id: "TD008",
                severity: "warning",
                target: t.name,
                message: "Code fence or inline examples embedded inside tool description.",
                wasted: w,
                suggestion: "Remove examples from always-loaded schemas; expose via MCP resources.",
              });
            }
            if (depth >= 5) {
              wasted += 20;
              findings.push({
                rule_id: "TD009",
                severity: "warning",
                target: t.name,
                message: `Deeply nested schema (depth ${depth}) adds overhead and argument errors.`,
                wasted: 20,
                suggestion: "Flatten nested objects where possible.",
              });
            }
            const sub = walkProperties(t.inputSchema, t.name, findings);
            wasted += sub.wasted;
            toolMetrics.push({ name: t.name, tokens: tt, descTokens: dt, schemaTokens: st });
          }

          toolMetrics.sort((a, b) => b.tokens - a.tokens);
          wasted = Math.min(wasted, Math.round(totalTokens * 0.75));
          const { score, grade } = scoreReport(totalTokens, findings, cacheSafe);
          return {
            kind: "mcp_tools",
            totalTokens,
            reducible: wasted,
            score,
            grade,
            cacheSafe,
            tools: toolMetrics,
            findings,
            parsedToolsPayload: parsed,
          };
        }

        if (parsed && typeof parsed === "object" && (parsed.mcpServers || parsed.servers)) {
          const servers = parsed.mcpServers || parsed.servers;
          const names = Object.keys(servers);
          const estTokens = names.length * 1450;
          const findings = [];
          let wasted = 0;
          if (names.length >= 8) {
            wasted = Math.round(estTokens * 0.45);
            findings.push({
              rule_id: "TD004",
              severity: "critical",
              target: "mcp.json",
              message: `${names.length} always-on MCP servers (~${estTokens.toLocaleString()} est. runtime tokens/turn).`,
              wasted,
              suggestion: "Split servers into task-specific profiles rather than loading all 8+ every session.",
            });
          } else if (names.length >= 4) {
            wasted = Math.round(estTokens * 0.3);
            findings.push({
              rule_id: "TD004",
              severity: "warning",
              target: "mcp.json",
              message: `${names.length} always-on MCP servers (~${estTokens.toLocaleString()} est. runtime tokens/turn).`,
              wasted,
              suggestion: "Disable unused tools per server.",
            });
          }
          const tools = names.map((n) => ({ name: `server:${n}`, tokens: 1450, descTokens: 450, schemaTokens: 1000 }));
          const { score, grade } = scoreReport(estTokens, findings, true);
          return {
            kind: "mcp_config",
            totalTokens: estTokens,
            reducible: wasted,
            score,
            grade,
            cacheSafe: true,
            tools,
            findings,
            parsedToolsPayload: null,
          };
        }
      } catch {
        // Fall through to text/Markdown analyzer
      }
    }

    // Markdown / Agent instruction file
    const totalTokens = countTokens(text);
    const findings = [];
    let cacheSafe = true;
    let wasted = 0;

    for (const [label, pat] of CACHE_BUSTERS) {
      const hits = text.match(pat);
      if (hits && hits.length) {
        cacheSafe = false;
        findings.push({
          rule_id: "TD005",
          severity: "critical",
          target: "instructions",
          message: `Prompt-cache-busting ${label} found (${hits.length}x) in static instruction prefix.`,
          wasted: 0,
          suggestion: "Move runtime timestamps and session IDs to the trailing user turn.",
        });
      }
    }

    if (totalTokens > 2500) {
      const w = Math.round(totalTokens * 0.28);
      wasted += w;
      findings.push({
        rule_id: "TD004",
        severity: totalTokens > 6000 ? "critical" : "warning",
        target: "instructions",
        message: `Always-loaded instruction file is ~${totalTokens.toLocaleString()} tokens (target <= 2,000).`,
        wasted: w,
        suggestion: "Extract deep checklists and samples into linked on-demand reference files.",
      });
    }

    const fences = text.match(/```[\s\S]*?```/g) || [];
    const fenceToks = fences.reduce((acc, b) => acc + countTokens(b), 0);
    if (fenceToks > 80) {
      const w = Math.round(fenceToks * 0.55);
      wasted += w;
      findings.push({
        rule_id: "TD008",
        severity: fenceToks > 400 ? "warning" : "info",
        target: "instructions",
        message: `Inline fenced code blocks consume ~${fenceToks.toLocaleString()} tokens (${fences.length} block(s)).`,
        wasted: w,
        suggestion: "Reference repository file paths instead of pasting boilerplate into system context.",
      });
    }

    const longLines = text.split("\n").map((l) => l.trim()).filter((l) => l.length >= 40);
    const lineFreq = new Map();
    for (const l of longLines) lineFreq.set(l, (lineFreq.get(l) || 0) + 1);
    let dupCount = 0;
    for (const [l, c] of lineFreq.entries()) {
      if (c >= 2) {
        dupCount += 1;
        wasted += countTokens(l) * (c - 1);
      }
    }
    if (dupCount > 0) {
      findings.push({
        rule_id: "TD007",
        severity: "warning",
        target: "instructions",
        message: `${dupCount} duplicated long directive line(s) detected.`,
        wasted: 0,
        suggestion: "Deduplicate repeated instructions.",
      });
    }

    const blankRuns = (text.match(/\n{3,}/g) || []).length;
    if (blankRuns >= 1) {
      wasted += blankRuns * 2;
      findings.push({
        rule_id: "TD012",
        severity: "info",
        target: "instructions",
        message: `${blankRuns} multi-blank-line padding block(s) detected.`,
        wasted: blankRuns * 2,
        suggestion: "Normalize vertical spacing.",
      });
    }

    wasted = Math.min(wasted, Math.round(totalTokens * 0.7));
    const { score, grade } = scoreReport(totalTokens, findings, cacheSafe);
    return {
      kind: "agent_instructions",
      totalTokens,
      reducible: wasted,
      score,
      grade,
      cacheSafe,
      tools: [
        { name: "Inline Code Fences", tokens: fenceToks, descTokens: fenceToks, schemaTokens: 0 },
        { name: "Prose & Directives", tokens: Math.max(0, totalTokens - fenceToks), descTokens: 0, schemaTokens: Math.max(0, totalTokens - fenceToks) },
      ],
      findings,
      parsedToolsPayload: null,
    };
  }

  /* --- Structure-preserving JSON Schema Minifier --- */
  function compactDescription(str, aggressive) {
    let s = str.replace(/```[\s\S]*?```/g, "");
    if (aggressive) {
      s = s.replace(/(?:\n+|\s+)(?:Examples?|For example|e\.g\.)\s*:[\s\S]*$/i, "");
      s = s.replace(/\bGenerated at 20\d{2}-\d{2}-\d{2}[^\s.]*\.?/gi, "");
      s = s.replace(/\bThis tool allows (?:you|the user|the agent) to\b/gi, "");
      s = s.replace(/\bUse this tool (?:when you want |whenever you need )?to\b/gi, "");
      s = s.replace(/\bPlease note that\b/gi, "Note:");
      s = s.replace(/\bMake sure (?:that )?you\b/gi, "Ensure");
      s = s.replace(/\bIn order to\b/gi, "To");
    }
    s = s.replace(/\s+/g, " ").replace(/^[,;:\-\s]+/, "").trim();
    if (aggressive && s.length > 0) s = s[0].toUpperCase() + s.slice(1);
    return s;
  }

  function cleanNode(node, keyName, aggressive) {
    if (Array.isArray(node)) return node.map((x) => cleanNode(x, "", aggressive));
    if (!node || typeof node !== "object") return node;
    const out = {};
    for (const k of Object.keys(node).sort()) {
      const v = node[k];
      if (k === "$schema") continue;
      if (k === "additionalProperties" && v === false) continue;
      if (k === "required" && Array.isArray(v) && v.length === 0) continue;
      if (k === "title" && typeof v === "string" && keyName) {
        if (v.toLowerCase().replace(/[^a-z0-9]/g, "") === keyName.toLowerCase().replace(/[^a-z0-9]/g, "")) {
          continue;
        }
      }
      if (k === "description" && typeof v === "string") {
        const c = compactDescription(v, aggressive);
        if (c) out[k] = c;
        continue;
      }
      if (k === "properties" && v && typeof v === "object") {
        const pOut = {};
        for (const pk of Object.keys(v).sort()) {
          pOut[pk] = cleanNode(v[pk], pk, aggressive);
        }
        out[k] = pOut;
        continue;
      }
      out[k] = cleanNode(v, k, aggressive);
    }
    return out;
  }

  function schemaSig(schema) {
    if (!schema || typeof schema !== "object") return schema;
    const out = {
      type: schema.type || null,
      required: Array.isArray(schema.required) ? [...schema.required].sort() : [],
    };
    if ("enum" in schema) out.enum = schema.enum;
    if (schema.properties && typeof schema.properties === "object") {
      out.properties = {};
      for (const k of Object.keys(schema.properties).sort()) {
        out.properties[k] = schemaSig(schema.properties[k]);
      }
    }
    if (schema.items && typeof schema.items === "object") out.items = schemaSig(schema.items);
    return out;
  }

  function payloadSig(payload) {
    const tools = extractTools(payload);
    if (!tools) return null;
    const map = {};
    for (const t of tools) map[t.name] = schemaSig(t.inputSchema);
    const sorted = {};
    for (const k of Object.keys(map).sort()) sorted[k] = map[k];
    return JSON.stringify(sorted);
  }

  function minifyPayload(payload, aggressive) {
    const beforeTok = countJsonTokens(payload);
    const beforeSig = payloadSig(payload);
    const cleaned = cleanNode(payload, "", aggressive);
    if (cleaned && Array.isArray(cleaned.tools)) {
      cleaned.tools.sort((a, b) =>
        String(a.name || a.function?.name || "").localeCompare(String(b.name || b.function?.name || ""))
      );
    } else if (Array.isArray(cleaned)) {
      cleaned.sort((a, b) =>
        String(a.name || a.function?.name || "").localeCompare(String(b.name || b.function?.name || ""))
      );
    }
    const afterSig = payloadSig(cleaned);
    const afterTok = countJsonTokens(cleaned);
    const saved = Math.max(0, beforeTok - afterTok);
    return {
      beforeTok,
      afterTok,
      saved,
      pct: beforeTok ? Math.round((saved / beforeTok) * 1000) / 10 : 0,
      invariantsOk: beforeSig === afterSig,
      pretty: JSON.stringify(cleaned, null, 2),
    };
  }

  function calcMonthlyCost(tokens, modelId, turnsPerDay, teamSize, cacheRatePct, cacheTtl) {
    const m = MODELS[modelId] || MODELS["claude-sonnet"];
    const hit = cacheRatePct / 100;
    const monthlyTokens = tokens * turnsPerDay * teamSize * 30;
    const missMult = cacheTtl === "1h" ? m.w1h : cacheTtl === "5m" ? m.w5m : 1.0;
    const rate = (1 - hit) * (m.input * missMult) + hit * m.cached;
    const usd = (monthlyTokens / 1_000_000) * rate;
    return { usd, gbp: usd * USD_TO_GBP };
  }

  /* --- DOM Wiring --- */
  const elInput = document.getElementById("payload-input");
  const elModel = document.getElementById("model-select");
  const elTurns = document.getElementById("turns-slider");
  const elTeam = document.getElementById("team-slider");
  const elCacheTtl = document.getElementById("cache-ttl-select");
  const elAggressive = document.getElementById("toggle-aggressive");

  let lastAudit = null;
  let lastMinified = null;

  function escapeHtml(str) {
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function render() {
    const text = elInput.value;
    const lines = text ? text.split("\n").length : 0;
    document.getElementById("input-stats").textContent = `${text.length.toLocaleString()} chars · ${lines.toLocaleString()} lines`;

    const turns = Number(elTurns.value);
    const team = Number(elTeam.value);
    const cacheTtl = elCacheTtl.value;
    document.getElementById("turns-val").textContent = String(turns);
    document.getElementById("team-val").textContent = String(team);

    const rep = auditText(text);
    lastAudit = rep;

    let effectiveSavedTokens = rep.reducible;
    if (rep.parsedToolsPayload) {
      lastMinified = minifyPayload(rep.parsedToolsPayload, elAggressive.checked);
      effectiveSavedTokens = Math.max(rep.reducible, lastMinified.saved);
      document.getElementById("minified-output").textContent = lastMinified.pretty;
      const badge = document.getElementById("invariant-badge");
      badge.textContent = lastMinified.invariantsOk
        ? `Invariants verified · -${lastMinified.saved} tok (-${lastMinified.pct}%)`
        : "Invariant mismatch";
      badge.className = lastMinified.invariantsOk ? "badge badge-save" : "badge badge-critical";
    } else {
      lastMinified = null;
      document.getElementById("minified-output").textContent =
        "// Paste an MCP tools/list or OpenAI/Anthropic tools[] JSON payload to generate a compacted schema.";
      document.getElementById("invariant-badge").textContent = "JSON tools required";
    }

    const kindMap = {
      mcp_tools: "Detected: MCP / LLM Tool Schema JSON",
      mcp_config: "Detected: MCP Server Config (mcp.json)",
      agent_instructions: "Detected: Agent Instruction Markdown",
      empty: "Input Payload (MCP JSON / Config / Markdown)",
    };
    document.getElementById("input-kind-label").textContent = kindMap[rep.kind] || kindMap.empty;

    const currentHitPct = rep.cacheSafe ? 80 : 0;
    const afterHitPct = 80;
    document.getElementById("cache-val").textContent = rep.cacheSafe ? "80% hit" : "0% (BROKEN)";

    const currentCost = calcMonthlyCost(rep.totalTokens, elModel.value, turns, team, currentHitPct, cacheTtl);
    const afterTokens = Math.max(0, rep.totalTokens - effectiveSavedTokens);
    const afterCost = calcMonthlyCost(afterTokens, elModel.value, turns, team, afterHitPct, cacheTtl);
    const savedMoUsd = Math.max(0, currentCost.usd - afterCost.usd);

    document.getElementById("kpi-tokens").textContent = rep.totalTokens.toLocaleString();
    const pctRed = rep.totalTokens ? Math.round((effectiveSavedTokens / rep.totalTokens) * 100) : 0;
    document.getElementById("kpi-reducible").textContent = `-${effectiveSavedTokens.toLocaleString()} tok (-${pctRed}%)`;

    const gradeEl = document.getElementById("kpi-grade");
    gradeEl.textContent = rep.kind === "empty" ? "—" : `${rep.grade} (${rep.score})`;
    gradeEl.className = "kpi-num " + (rep.score >= 78 ? "is-save" : rep.score < 50 ? "is-danger" : "");
    document.getElementById("kpi-cache").textContent = rep.kind === "empty" ? "Cache: —" : rep.cacheSafe ? "Cache: Safe" : "Cache: BROKEN";

    document.getElementById("kpi-burn").textContent = `$${currentCost.usd.toFixed(2)}`;
    document.getElementById("kpi-burn-gbp").textContent = `£${currentCost.gbp.toFixed(2)} GBP / mo`;

    document.getElementById("kpi-savings").textContent = `$${savedMoUsd.toFixed(2)}`;
    document.getElementById("kpi-savings-yr").textContent = `$${(savedMoUsd * 12).toFixed(0)} / yr saved`;

    // Findings list
    document.getElementById("tab-findings-count").textContent = String(rep.findings.length);
    const fc = document.getElementById("findings-container");
    if (!rep.findings.length) {
      fc.innerHTML = `<div class="finding-item"><p class="finding-msg">No bloat or cache-busting issues detected.</p></div>`;
    } else {
      fc.innerHTML = rep.findings
        .map(
          (f) => `
        <div class="finding-item">
          <div class="finding-head">
            <span class="badge badge-${f.severity}">${escapeHtml(f.severity)}</span>
            <span class="badge badge-info">${escapeHtml(f.rule_id)}</span>
            <span class="finding-target">${escapeHtml(f.target)}</span>
          </div>
          <p class="finding-msg">${escapeHtml(f.message)}</p>
          <p class="finding-fix">${escapeHtml(f.suggestion)}</p>
        </div>`
        )
        .join("");
    }

    // Bars breakdown
    const bc = document.getElementById("bars-container");
    const maxTok = rep.tools.length ? Math.max(...rep.tools.map((t) => t.tokens), 1) : 1;
    if (!rep.tools.length) {
      bc.innerHTML = `<p class="finding-fix">No tools or sections detected yet.</p>`;
    } else {
      bc.innerHTML = rep.tools
        .map((t) => {
          const descPct = Math.round((t.descTokens / maxTok) * 100);
          const schPct = Math.round((t.schemaTokens / maxTok) * 100);
          return `
          <div class="bar-row">
            <div class="bar-meta">
              <span class="bar-name">${escapeHtml(t.name)}</span>
              <span class="bar-val">${t.tokens.toLocaleString()} tok</span>
            </div>
            <div class="bar-track">
              <div class="bar-seg-desc" style="width:${descPct}%"></div>
              <div class="bar-seg-schema" style="width:${schPct}%"></div>
            </div>
          </div>`;
        })
        .join("");
    }
  }

  /* --- Dual-Rail Checkout Loader (Live Base Mainnet USDC + Stripe TAN Payment Link) --- */
  const TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef";
  let checkoutCfg = null;
  let activeOrderTier = "pro"; // "pro" | "audit"

  function openUsdcModal(tier) {
    if (!checkoutCfg || !checkoutCfg.onchain_usdc) return;
    activeOrderTier = tier;
    const oc = checkoutCfg.onchain_usdc;
    const isAudit = tier === "audit";
    const amount = isAudit ? oc.audit_amount_usdc : oc.pro_amount_usdc;
    const units = BigInt(amount) * 1000000n;
    document.getElementById("modal-item-name").textContent = isAudit
      ? "Done-For-You MCP & Prompt-Cache Audit (+ Pro Kit)"
      : checkoutCfg.product_name;
    document.getElementById("modal-item-price").textContent = `${amount}.00 USDC`;
    document.getElementById("modal-treasury-addr").textContent = oc.treasury_address;
    document.getElementById("modal-eip681-link").href =
      `ethereum:${oc.token_contract}@${oc.chain_id}/transfer?address=${oc.treasury_address}&uint256=${units.toString()}`;
    document.getElementById("modal-basescan-addr").href = `https://basescan.org/address/${oc.treasury_address}`;
    const resBox = document.getElementById("verify-result");
    resBox.className = "verify-result";
    resBox.textContent = "";
    document.getElementById("tx-hash-input").value = "";
    document.getElementById("usdc-modal").classList.add("is-open");
  }

  async function verifyBaseUsdcTx() {
    const resBox = document.getElementById("verify-result");
    const txHash = document.getElementById("tx-hash-input").value.trim();
    if (!/^0x[0-9a-fA-F]{64}$/.test(txHash)) {
      resBox.className = "verify-result is-err";
      resBox.textContent = "Please enter a valid 66-character Base Mainnet transaction hash (0x...).";
      return;
    }
    const oc = checkoutCfg.onchain_usdc;
    const requiredAmount = activeOrderTier === "audit" ? oc.audit_amount_usdc : oc.pro_amount_usdc;
    const requiredUnits = BigInt(requiredAmount) * 1000000n;
    resBox.className = "verify-result";
    resBox.style.display = "block";
    resBox.textContent = "Querying Base Mainnet RPC (https://mainnet.base.org)...";

    try {
      const resp = await fetch(oc.rpc_url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "eth_getTransactionReceipt", params: [txHash] }),
      });
      const data = await resp.json();
      const receipt = data.result;
      if (!receipt) {
        resBox.className = "verify-result is-err";
        resBox.textContent = "Transaction not found or still pending on Base Mainnet. Wait ~5 seconds and retry.";
        return;
      }
      if (receipt.status !== "0x1") {
        resBox.className = "verify-result is-err";
        resBox.textContent = "Transaction reverted on-chain (status != 0x1).";
        return;
      }
      const targetAddr = oc.treasury_address.toLowerCase().replace(/^0x/, "");
      const usdcAddr = oc.token_contract.toLowerCase();
      let matchedUnits = 0n;
      for (const log of receipt.logs || []) {
        if (
          (log.address || "").toLowerCase() === usdcAddr &&
          Array.isArray(log.topics) &&
          log.topics.length >= 3 &&
          log.topics[0].toLowerCase() === TRANSFER_TOPIC &&
          log.topics[2].toLowerCase().endsWith(targetAddr)
        ) {
          matchedUnits += BigInt(log.data || "0x0");
        }
      }
      if (matchedUnits < requiredUnits) {
        const paidStr = (Number(matchedUnits) / 1e6).toFixed(2);
        resBox.className = "verify-result is-err";
        resBox.textContent = `Verified receipt on Base, but USDC sent to TAN Treasury was ${paidStr} USDC (required: ${requiredAmount}.00 USDC).`;
        return;
      }
      const paidUsdc = (Number(matchedUnits) / 1e6).toFixed(2);
      const claimTitle = encodeURIComponent(
        `[PAID ON-CHAIN ${paidUsdc} USDC] ${activeOrderTier === "audit" ? "Done-For-You Audit" : "TAN TokenDiet Pro"} Fulfillment`
      );
      const claimBody = encodeURIComponent(
        `Verified Base Mainnet USDC payment:\n- Amount: ${paidUsdc} USDC\n- Tx Hash: ${txHash}\n- BaseScan: https://basescan.org/tx/${txHash}\n\nPlease deliver the Pro Kit / Audit access.`
      );
      const claimUrl = `https://github.com/20171806011/tan-tokendiet/issues/new?title=${claimTitle}&body=${claimBody}`;
      resBox.className = "verify-result is-ok";
      resBox.innerHTML =
        `<strong>Confirmed on Base Mainnet: ${paidUsdc} USDC received!</strong><br/>` +
        `<a href="${claimUrl}" target="_blank" rel="noopener" style="font-weight:700;color:var(--accent-save);">Click here to claim instant delivery with verified Tx Hash →</a>`;
    } catch (err) {
      resBox.className = "verify-result is-err";
      resBox.textContent = `RPC check failed: ${err.message || err}`;
    }
  }

  async function initCheckout() {
    const btn = document.getElementById("btn-buy-pro");
    const note = document.getElementById("checkout-status-note");
    const auditBtn = document.getElementById("btn-buy-audit");
    try {
      const resp = await fetch("./checkout-config.json", { cache: "no-store" });
      const cfg = await resp.json();
      checkoutCfg = cfg;
      document.getElementById("pro-price-display").textContent = `£${cfg.price_gbp}`;
      document.getElementById("pro-price-sub").textContent = `GBP ($${cfg.price_usd} USDC) · one-time · v1.x`;

      if (cfg.checkout_url) {
        btn.href = cfg.checkout_url;
        btn.target = "_blank";
        btn.rel = "noopener";
        btn.textContent = `Buy TokenDiet Pro — £${cfg.price_gbp} (Card / Apple Pay)`;
        note.innerHTML = `Instant Stripe Checkout · or <a href="#pricing" id="inline-usdc-pro">pay $${cfg.price_usd} USDC on Base</a>.`;
        document.getElementById("inline-usdc-pro")?.addEventListener("click", (e) => {
          e.preventDefault();
          openUsdcModal("pro");
        });
      } else if (cfg.onchain_usdc && cfg.onchain_usdc.enabled) {
        btn.href = "#pricing";
        btn.textContent = `Buy TokenDiet Pro — $${cfg.onchain_usdc.pro_amount_usdc} USDC (Base · Live)`;
        btn.addEventListener("click", (e) => {
          e.preventDefault();
          openUsdcModal("pro");
        });
        note.innerHTML = `Live 24/7 on-chain Base USDC checkout (2s finality, &lt;$0.01 fee) · <a href="${cfg.preorder_url}" target="_blank" rel="noopener">Card/Stripe waitlist</a>.`;
      } else {
        btn.href = cfg.preorder_url || "https://github.com/20171806011/tan-tokendiet/issues";
        btn.target = "_blank";
        btn.rel = "noopener";
        btn.textContent = `Reserve Pro License (£${cfg.price_gbp})`;
        note.textContent = "Click to request license via GitHub.";
      }

      if (auditBtn && cfg.onchain_usdc && cfg.onchain_usdc.enabled) {
        auditBtn.addEventListener("click", () => openUsdcModal("audit"));
      }
    } catch {
      btn.href = "https://github.com/20171806011/tan-tokendiet/issues";
      btn.textContent = "Buy TokenDiet Pro — £15 / $19";
    }
  }

  document.getElementById("btn-close-modal")?.addEventListener("click", () => {
    document.getElementById("usdc-modal").classList.remove("is-open");
  });
  document.getElementById("usdc-modal")?.addEventListener("click", (ev) => {
    if (ev.target.id === "usdc-modal") ev.target.classList.remove("is-open");
  });
  document.getElementById("btn-copy-treasury")?.addEventListener("click", async (ev) => {
    const addr = document.getElementById("modal-treasury-addr").textContent;
    try {
      await navigator.clipboard.writeText(addr);
      ev.target.textContent = "Copied";
      setTimeout(() => (ev.target.textContent = "Copy"), 1500);
    } catch {}
  });
  document.getElementById("btn-verify-tx")?.addEventListener("click", verifyBaseUsdcTx);

  /* --- Event Listeners --- */
  function setSample(key, btnId) {
    elInput.value = SAMPLES[key];
    document.querySelectorAll("#sample-mcp, #sample-agents, #sample-config").forEach((b) => b.classList.remove("is-active"));
    document.getElementById(btnId).classList.add("is-active");
    render();
  }

  document.getElementById("sample-mcp").addEventListener("click", () => setSample("mcp", "sample-mcp"));
  document.getElementById("sample-agents").addEventListener("click", () => setSample("agents", "sample-agents"));
  document.getElementById("sample-config").addEventListener("click", () => setSample("config", "sample-config"));
  document.getElementById("btn-clear").addEventListener("click", () => {
    elInput.value = "";
    render();
  });

  document.getElementById("file-upload").addEventListener("change", (ev) => {
    const file = ev.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      elInput.value = String(reader.result || "");
      render();
    };
    reader.readAsText(file);
  });

  [elInput, elModel, elTurns, elTeam, elCacheTtl, elAggressive].forEach((el) => {
    el.addEventListener("input", render);
    el.addEventListener("change", render);
  });

  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("is-active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("is-active"));
      btn.classList.add("is-active");
      document.getElementById(`panel-${btn.dataset.tab}`).classList.add("is-active");
    });
  });

  document.getElementById("btn-copy-cli").addEventListener("click", async (ev) => {
    const cmd = document.getElementById("cli-install-cmd").textContent;
    try {
      await navigator.clipboard.writeText(cmd);
      ev.target.textContent = "Copied";
      setTimeout(() => (ev.target.textContent = "Copy"), 1500);
    } catch {}
  });

  document.getElementById("btn-copy-minified").addEventListener("click", async (ev) => {
    if (!lastMinified) return;
    try {
      await navigator.clipboard.writeText(lastMinified.pretty);
      ev.target.textContent = "Copied";
      setTimeout(() => (ev.target.textContent = "Copy JSON"), 1500);
    } catch {}
  });

  document.getElementById("btn-download-minified").addEventListener("click", () => {
    if (!lastMinified) return;
    const blob = new Blob([lastMinified.pretty + "\n"], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "tools.compact.json";
    a.click();
    URL.revokeObjectURL(a.href);
  });

  document.getElementById("btn-export-report").addEventListener("click", () => {
    if (!lastAudit) return;
    const m = MODELS[elModel.value];
    const md = [
      `# TAN TokenDiet Audit Report`,
      ``,
      `- **Detected Kind:** \`${lastAudit.kind}\``,
      `- **Tokens / Turn:** ${lastAudit.totalTokens.toLocaleString()}`,
      `- **Health Score:** ${lastAudit.score}/100 (Grade ${lastAudit.grade})`,
      `- **Prompt-Cache Safe:** ${lastAudit.cacheSafe ? "YES" : "NO"}`,
      `- **Model:** ${m.name} (${elTurns.value} turns/day × ${elTeam.value} devs)`,
      `- **Current Monthly Burn:** ${document.getElementById("kpi-burn").textContent} (${document.getElementById("kpi-burn-gbp").textContent})`,
      `- **Projected Monthly Savings:** ${document.getElementById("kpi-savings").textContent}`,
      ``,
      `## Findings (${lastAudit.findings.length})`,
      ...lastAudit.findings.map((f) => `- **[${f.severity.toUpperCase()} · ${f.rule_id}]** \`${f.target}\`: ${f.message} → *${f.suggestion}*`),
      ``,
      `Generated locally by [TAN TokenDiet](https://20171806011.github.io/tan-tokendiet/).`,
    ].join("\n");
    const blob = new Blob([md], { type: "text/markdown" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "tokendiet-audit-report.md";
    a.click();
    URL.revokeObjectURL(a.href);
  });

  // Boot with realistic MCP sample
  setSample("mcp", "sample-mcp");
  initCheckout();
})();
