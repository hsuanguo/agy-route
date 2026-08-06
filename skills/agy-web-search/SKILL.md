---
name: agy-web-search
description: "Perform a grounded web search via the agy CLI (Gemini). Trigger when: (1) user explicitly asks for agy-web-search, (2) user mentions Gemini or Antigravity search, (3) a second search opinion from Google is needed, or (4) built-in search fails or returns insufficient results."
user-invocable: false
---

# AGY Web Search

Routes web searches through `agy-route search` so queries execute on Gemini with grounded web search and return source citations.

## Trigger Criteria

Use this skill when:
1. **Explicit Request**: The user explicitly asks for `agy-web-search`, `/agy-web-search`, or `agy search`.
2. **Gemini / Antigravity Search**: The user mentions Gemini search, Google Antigravity search, or grounded search.
3. **Second Opinion**: A second search opinion from Google is needed to cross-check or verify findings.
4. **Fallback**: The built-in web search tool fails, times out, or returns incomplete/insufficient results.

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