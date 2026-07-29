---
description: Multi-source deep research via agy-route. Plan → fan-out fetch → URL-quote verification → cited synthesis. The only agy-backed primitives are fetch and quote; plan/verify/synthesize are Claude reasoning.
argument-hint: "<topic>"
---

You are running a deep-research pass on the topic below. Follow the **agy-route deep-research recipe** step by step.

Topic: $ARGUMENTS

If the topic is empty, ask the user what to research (AskUserQuestion) before proceeding.

## Step 1 — Plan (your job)

Decompose the topic into **3–6 sub-questions**. Identify which 1–3 are **load-bearing claims** that need URL-quote verification (the rest are background context). Output as plain markdown:

```
Sub-questions:
1. <q1>
2. <q2>
…

Load-bearing claims to verify:
- <claim A>  [needs ≥2 independent sources]
- <claim B>  [needs ≥2 independent sources]
```

## Step 2 — Fan-out fetch (parallel Bash)

For each sub-question, run **in parallel** via the Bash tool:

```bash
agy-route research fetch "<sub-question>"
```

Force compact output: each call returns 5–8 bullets, each with the exact source URL and publication date. Don't synthesize here. If a call times out or returns empty, retry once with `--timeout 600`; if still empty, mark that sub-question "low-confidence" and move on.

(Note: agy may summarize rather than return full page content. That's fine — we deepen in Step 3.)

## Step 3 — URL-quote verification (per load-bearing claim)

For each load-bearing claim, pick the URL(s) from Step 2 that look like they support it. Then for each (claim, URL) pair, run via Bash:

```bash
agy-route research quote "<claim>" "<url>"
```

This asks agy to open the URL and quote the **exact sentence(s)** supporting the claim — or reply `NOT SUPPORTED` if the page doesn't actually back it. Parallelize across (claim, URL) pairs.

## Step 4 — Adversarial verify (your job)

For each load-bearing claim, decide:
- **verified** — at least 2 independent domains each quoted a sentence that supports the claim (not just paraphrased or vaguely "supports" it)
- **unverified** — only one source quoted; the quote is a paraphrase / parametric knowledge / doesn't actually support the claim; or all URLs returned `NOT SUPPORTED`

**Watch for:** agy quoting generic "common knowledge" phrases (e.g. "Yes, this is a well-known fact that…") — those are paraphrases, not URL quotes. Mark unverified.

## Step 5 — Synthesize

Write the final cited report:

```
## <Topic>

### Summary
<2-3 sentence summary>

### Verified findings
- **<claim>**: <quoted sentence> — <url> (<date>)
- **<claim>**: <quoted sentence> — <url> (<date>)
…

### Unverified
- <claim>: only one source / quote was parametric / no source returned support

### Sources
- <url 1>
- <url 2>
…
```

## Token economics

Bulky search/fetch text is paid in cheap Gemini tokens. Keep your own context lean — ingest the bullets and quotes, not raw agy output. Re-dispatch Step 2/3 calls if evidence is thin; don't expect auto-iteration in a single call.

## Output

Return the final report to the user as your response. Do not run any other commands after synthesis.