---
name: agy-research
description: Perform multi-source deep research on a topic via agy-route research primitives (fetch + quote). Use when asked to research, investigate, do a deep dive, or gather multi-source evidence on a topic.
user-invocable: false
---

# AGY Route Research

Multi-source deep research using `agy-route` primitives and AI Agent reasoning.

## The 5-Step Recipe

| Step | Responsible | Tool / Method |
|---|---|---|
| 1. Plan | AI Agent | Decompose topic into 3–6 sub-questions in context |
| 2. Fan-out fetch | agy (parallel) | `agy-route research fetch "<sub-question>"` |
| 3. URL-quote verify | agy (parallel) | `agy-route research quote "<claim>" "<url>"` |
| 4. Adversarial verify | AI Agent | Evaluate quotes; mark as verified (≥2 independent sources) or unverified |
| 5. Synthesize | AI Agent | Write a cited research report with verbatim quotes and source URLs |

## Execution Details

### Step 1 — Plan
Break the query down into 3–6 distinct sub-questions and identify key load-bearing claims.

### Step 2 — Fan-out Fetch
Run sub-question searches in parallel via Bash:

```bash
agy-route research fetch "<sub-question>"
```

Returns 5–8 bullet findings with exact URLs and publication dates.

### Step 3 — URL-Quote Verification
Verify key claims against candidate URLs in parallel via Bash:

```bash
agy-route research quote "<claim>" "<url>"
```

Returns verbatim supporting sentences or `NOT SUPPORTED`.

### Step 4 — Adversarial Verification
- **Verified**: Supported by exact quotes from ≥2 independent source domains.
- **Unverified**: Single source, missing quotes, or vague claims.

### Step 5 — Synthesize Report
Output the final report containing summary, verified findings (with quotes and URLs), unverified claims, and full source list.