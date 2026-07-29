---
name: agy-route-research
description: Use when the user asks Claude to research, investigate, or look up multiple sources on a topic — "research X", "investigate Y", "look into Z", "what does the evidence say about …", "do a deep dive on …", "find me sources for …". Runs the deep-research recipe via agy-route's research primitives (fetch + quote) + Claude's own plan/verify/synthesize reasoning. The hook handles single-shot search; this skill handles multi-source research.
---

# AGY Route Research

Multi-source deep research via `agy-route`. Two agy-backed primitives + three Claude-reasoning steps.

## The recipe

| step | who | tool |
|---|---|---|
| 1. Plan | Claude | reasoning in context — no CLI |
| 2. Fan-out fetch | agy (parallel) | `agy-route research fetch "<sub-question>"` |
| 3. URL-quote verify | agy (parallel) | `agy-route research quote "<claim>" "<url>"` |
| 4. Adversarial verify | Claude | reasoning in context — no CLI |
| 5. Synthesize | Claude | reasoning in context — no CLI |

## When to use

Use the recipe when the user asks for **multi-source** research: "research X", "investigate Y", "find sources for Z", "do a deep dive on W", "what's the evidence for V". The key signal: the user wants a **cited report**, not a single answer.

Do **not** use this for:
- Single-fact lookups ("what year was X founded") — use `agy-route search` (the hook handles it).
- Stable parametric knowledge — answer directly.

## How it works

### Step 1 — Plan (your job)

Decompose the topic into 3–6 sub-questions. Identify 1–3 load-bearing claims that need ≥2 independent sources.

### Step 2 — Fan-out fetch (parallel Bash)

```bash
agy-route research fetch "<sub-question>"
```

Returns 5–8 bullet findings, each with URL + publication date. Run **in parallel** for all sub-questions.

### Step 3 — URL-quote verification (parallel Bash)

```bash
agy-route research quote "<claim>" "<url>"
```

For each (load-bearing claim, candidate URL) pair, ask agy to open the URL and quote the exact sentence(s) supporting the claim — or `NOT SUPPORTED` if the page doesn't actually back it. Parallelize across pairs.

### Step 4 — Adversarial verify (your job)

For each load-bearing claim:
- **verified** — ≥2 independent domains each quoted a sentence that supports the claim
- **unverified** — single source, vague citation, paraphrase, parametric knowledge, or all URLs returned `NOT SUPPORTED`

Watch for paraphrases of "common knowledge" — those are not URL quotes.

### Step 5 — Synthesize

Write a cited report:

```
## <Topic>

### Summary
<2-3 sentence summary>

### Verified findings
- **<claim>**: "<exact quote>" — <url> (<date>)
…

### Unverified
- <claim>: <reason>

### Sources
- <url>
…
```

## Token economics

Bulky search/fetch/quote text is paid in cheap Gemini tokens. Keep your own context lean — ingest bullets + quotes, not raw pages. Re-dispatch Step 2/3 calls if evidence is thin.

## Common mistakes

| Symptom | Fix |
|---|---|
| agy returns paraphrase, not quote | Mark unverified. Push agy harder: re-run `agy-route research quote` with the claim + URL explicitly. |
| Single-source claim | Mark unverified. Step 2 fan-out didn't find enough independent domains. |
| `Exit 124` (timeout) | `agy-route research quote` defaults to 300 s. Re-run with `--timeout 600`. |
| agy summarizes instead of quoting | The `quote` prompt forces `read_url`/`read_url_content`. If the model still summarizes, re-run; if still, mark unverified. |
| Step 2 fan-out returns empty | Retry with `--timeout 600`. If still empty, mark sub-question low-confidence and continue. |

## Privacy

Prompts are sent to Google's Gemini service via agy. Do **not** pipe credentials, API keys, or PII into any of the research primitives.