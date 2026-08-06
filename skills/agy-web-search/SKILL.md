---
name: agy-web-search
description: Perform a grounded web search via the agy CLI (Gemini) with real source citations. Use when asked to search the web, look up current information, verify claims against live sources, or find documentation/citations.
---

# AGY Web Search

Routes web searches through `agy-route search` so queries execute on Gemini with grounded web search and return source citations.

## Usage

Run via the Bash tool:

```bash
agy-route search "your search query here"
```

For long or multi-line prompts, pipe via stdin:

```bash
echo "your search query" | agy-route search
```

## Guidelines

- **Always include citations**: `agy-route search` returns a synthesized answer with source URLs and publication dates. Include these exact source URLs and dates in your response to the user.
- **Do not use for stable knowledge**: Use direct parametric knowledge for fundamental syntax, basic math, or established facts. Reaching for `agy-route search` is for live, current, or documentation-specific information.
- **Model selection**: Defaults to Gemini's latest flash search model. Pass `--model <name>` to override.