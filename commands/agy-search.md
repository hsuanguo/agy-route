---
description: Run a web search via the agy CLI (Gemini, grounded, cited). Drop-in for Claude's built-in WebSearch tool.
argument-hint: "<query>"
---

Run a grounded web search through `agy-route search`. agy (Google Antigravity CLI) calls Gemini with `search_web` enabled, so the result comes back with real source URLs and dates — not parametric recall.

Query: $ARGUMENTS

If `$ARGUMENTS` is empty, ask the user what to search for before running.

Run via `Bash`:

```bash
agy-route search "$ARGUMENTS"
```

Return the full response **including all source URLs verbatim**. Do not paraphrase citations, do not drop dates, do not summarize URLs as "various sources" — the user asked for a search, give them the search result.

If `agy-route` is not on `$PATH`, install it once with `uv tool install git+https://github.com/hsuanguo/agy-route`, then retry.