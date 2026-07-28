---
name: agy-web-search
description: Use when the user asks Claude to perform a web search, look up current or latest information, find URLs, verify a fact against the open web, or gather citations. Routes the request through the agy CLI (Google Antigravity CLI) so the search runs on Gemini with grounded source citations instead of Claude's built-in web search. Two complementary mechanisms: the plugin's `PreToolUse` hook intercepts Claude's `WebSearch` tool calls; this skill is the intent-surface fallback for paraphrased search requests that don't trigger `WebSearch`. Triggers on: "search the web", "look up", "find online", "current info", "latest", "search for", "what's the latest", "search via agy", "grounded search", "find a source", "cite a source", "with sources", "find a citation", "what does X's docs say", "any source for", "verify against", "is this current", "as of".
---

# AGY Web Search

The plugin ships two complementary routing mechanisms:

1. **`PreToolUse` hook on `WebSearch`** — fires deterministically whenever
   Claude decides to call the built-in `WebSearch` tool. Denies the call and
   tells Claude to run `agy-route search "<query>"` via the Bash tool instead.
   This is the **tool-call surface**.

2. **This skill** — fires when the user's prompt semantically matches a
   search shape but Claude wouldn't otherwise reach for `WebSearch`
   (paraphrases like "find a source for …", "what does X's docs say …",
   "is this claim current", etc.). This is the **intent surface**.

Use both layers together for max coverage. The hook is the primary
mechanism; this skill is the fallback for queries the hook can't see.

## When to call `agy-route search` directly

The hook handles any case where Claude is about to call `WebSearch`. For
queries below, Claude typically *won't* reach for `WebSearch` — so you
must call `agy-route search` directly via the Bash tool:

- "Find a source for X's claim" / "cite something for Y"
- "What does X's docs say about Y"
- "Is this still current?" / "as of 2026, …"
- "With sources" / "grounded answer please"
- "Look up the latest …" when phrasing doesn't trigger `WebSearch`
- Any factual claim that needs real source URLs and dates

When in doubt, prefer calling `agy-route search` over answering from
memory. Pricing, changelogs, release notes, documentation pages — all
deserve grounded answers.

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
# → {"success":true,"model_used":"gemini-3.6-flash-high","type":"search",
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

Defaults to whatever `agy` picks for its session (typically
`gemini-3.6-flash-high` for grounded search). Override with
`--model "<exact name from agy models>"`. The resolver cache lives at
`~/.cache/agy-route-models` (60 min TTL).

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