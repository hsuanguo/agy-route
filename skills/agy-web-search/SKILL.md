---
name: agy-web-search
description: Reference for the agy-route wrapper. The plugin's hook auto-routes Claude's WebSearch tool to `agy-route search`; this skill documents what `agy-route` is, when to call it directly via Bash, and how to interpret its output. The skill is a fallback + reference layer — the hook does the actual routing.
---

# AGY Web Search — `agy-route` reference

The plugin ships a `PreToolUse` hook that intercepts Claude's `WebSearch`
tool calls and reroutes them to `agy-route search` (a policy-gated,
grounded alternative that uses the agy CLI's `search_web` tool with
source citations). That hook is the primary mechanism — Claude never
needs to know about `agy-route` for web search to be routed correctly.

This skill remains as a reference layer for two cases:

1. **Hook is disabled** — if a user turns the hook off (or it fails to
   register because `agy-route` is not installed), Claude can still
   call `agy-route search` directly via the Bash tool.
2. **Direct call is cleaner** — for queries where Claude would
   otherwise reach for a different tool (e.g. a paraphrased "find me a
   source for …" that wouldn't trigger `WebSearch`), Claude may
   decide to invoke `agy-route search` directly via Bash.

## When to call `agy-route search` directly

- Factual claims that need real source URLs and dates.
- Pricing, changelogs, release notes, documentation pages.
- Anything where the user asks for "with sources" or "cited".

Do **not** reach for `agy-route` for stable parametric knowledge
(programming language syntax, math fundamentals, established science) —
answer directly, no tool call.

## How to call it

The wrapper is installed via
`uv tool install git+https://github.com/hsuanguo/agy-route`. It wraps
`agy --print` with a search-only tool policy and a Gemini prompt prefix
that forces a real `search_web` call.

```bash
# Inline
agy-route search "latest Antigravity CLI release"

# Piped prompt (safer for long queries)
echo "What changed in Python 3.13 between rc1 and final?" | agy-route search

# JSON envelope
echo "query" | agy-route search --json
# → {"success":true,"model_used":"gemini-3.5-flash-high","type":"search",
#    "duration_seconds":9,"response":"...citations..."}
```

## Result format

`agy-route search` returns plain text: a synthesized answer plus a list
of source URLs with publication dates. **Echo the citations back to the
user verbatim** — do not paraphrase URLs or dates, and do not strip them
when the user asked for "the answer".

For programmatic use, pass `--json` to get the
`{"success", "model_used", "type", "duration_seconds", "response"}`
envelope.

## Model

Defaults to the latest `gemini-*-flash-high` resolved from `agy models`
(cached 60 min at `~/.cache/agy-route-models`). Override with
`--model "<exact name from agy models>"`. Override the resolution cache
by deleting that file.

## Common mistakes

| Symptom | Fix |
|---|---|
| `agy-route: command not found` | Wrapper not installed — `uv tool install git+https://github.com/hsuanguo/agy-route`. |
| Hook didn't intercept a `WebSearch` call | The hook matches `WebSearch` only. `WebFetch` (direct URL fetch) is left alone — call `agy-route search` manually if you want grounded results for a known URL. |
| Empty reply / `Exit 3` | Quota or auth — check stderr; the JSON envelope includes `error_class` when `--json` is set. |
| Calling raw `agy` directly | Use `agy-route` — direct calls skip the search-only tool policy. |

## Privacy

Do **not** pipe content containing credentials, API keys, or PII into
`agy-route`. The prompt is sent to Google's Gemini service.