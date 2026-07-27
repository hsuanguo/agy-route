---
name: agy-web-search
description: Use when Claude is asked to perform a web search, look up current or latest information, find URLs, verify a fact against the open web, or gather citations. Routes the request through the agy CLI (Google Antigravity CLI) so the search runs on Gemini with grounded source citations instead of Claude's built-in web search. Triggers on: "search the web", "look up", "find online", "current info", "latest", "search for", "what's the latest", "search via agy", "grounded search", "find a source", "cite a source".
---

# AGY Web Search

This skill routes web searches through the **agy CLI** (Google Antigravity CLI, Gemini under the hood) so every search returns grounded, source-cited results. When the skill is active, prefer `agy-route search` over Claude's built-in `WebSearch` / `web_search` tool.

## When to use it

Use `agy-route search` whenever the answer depends on current or external information:

- "What's the latest …", "current price of …", "what changed in release X"
- Factual claims that need real source URLs and dates
- Pricing, changelogs, release notes, documentation pages
- Anything where the user asks for "with sources" or "cited"

Do **not** use it for stable, parametric knowledge (programming language syntax, math fundamentals, established science). For those, answer directly — no tool call needed.

## How to call it

The wrapper `agy-route` is installed via `uv tool install git+https://github.com/hsuanguo/agy-harness` once per machine. It wraps `agy --print` with a search-only tool policy and a Gemini prompt prefix that forces a real `search_web` call.

```bash
# One-shot inline
agy-route search "latest Antigravity CLI release"

# With a piped prompt (safer for long queries)
echo "What changed in Python 3.13 between rc1 and final?" | agy-route search

# JSON envelope for programmatic callers
echo "query" | agy-route search --json
# → {"success":true,"model_used":"gemini-3.5-flash-high","type":"search",
#    "duration_seconds":9,"response":"...citations..."}
```

If `agy-route` is not on `$PATH`, tell the user to run `uv tool install git+https://github.com/hsuanguo/agy-harness` once. Until then, fall back to Claude's built-in `WebSearch` tool — never call raw `agy` (you'll lose type routing, tool policy, and exit-code normalization).

## Result format

`agy-route search` returns plain text: a synthesized answer plus a list of source URLs with publication dates. **Echo the citations back to the user verbatim** — do not paraphrase URLs or dates, and do not strip them when the user asked for "the answer".

For programmatic use, pass `--json` to get the `{"success", "model_used", "type", "duration_seconds", "response"}` envelope.

## Model

Defaults to the latest `gemini-*-flash-high` resolved from `agy models` (cached 60 min at `~/.cache/agy-route-models`). Override with `--model "<exact name from agy models>"`. Override the resolution cache by deleting that file.

## Common mistakes

| Symptom | Fix |
|---|---|
| `agy-route: command not found` | Wrapper not installed — `uv tool install git+https://github.com/hsuanguo/agy-harness`. Until fixed, fall back to built-in WebSearch. |
| Response has no source URLs | The model skipped the search — re-run; the search-only policy forces `search_web`. |
| `Exit 124` (timeout) | Default 300 s; pass `--timeout 600` for slower queries. |
| `Exit 13` (`agy-missing`) | `agy` not on PATH — install it (https://antigravity.google/docs/cli-using). |
| `Exit 14` (`model-unavailable`) | Cached model id stale — `rm ~/.cache/agy-route-models` and retry. |
| Empty reply / `Exit 3` | Quota or auth — check stderr; the JSON envelope includes `error_class` when `--json` is set. |
| Calling raw `agy` directly | Use `agy-route` — direct calls skip the search-only tool policy. |

## Privacy

Do **not** pipe content containing credentials, API keys, or PII into `agy-route`. The prompt is sent to Google's Gemini service.