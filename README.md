# agy-route — `agy-web-search` plugin

<p align="left">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo.svg">
    <img alt="agy-route" src="assets/logo.svg" width="320">
  </picture>
</p>

A Claude Code plugin that **routes web searches through the `agy` CLI** (Google
Antigravity CLI — Gemini under the hood). When this plugin is enabled, Claude's
built-in `WebSearch` tool is intercepted by a `PreToolUse` hook and rerouted to
`agy-route search`, which uses `agy`'s grounded web search with real source
citations.

This is the first plugin in the [`agy-route`](.) repo. Future plugins (review,
research, …) become subcommands of the same `agy-route` binary.

> **You don't need to install the Claude Code marketplace.**
> The repo ships a `.claude-plugin/marketplace.json` so anyone who *wants*
> the marketplace path can `/plugin marketplace add
> https://github.com/hsuanguo/agy-route`, but it's **opt-in**. The
> recommended install is the **lite path** below — two commands, no
> marketplace, no plugin registry. Pick the marketplace path only if you want
> the `/agy-search` slash command, versioned `/plugin update`, or to appear
> in `/plugin marketplace browse`.

## What you get

- **`PreToolUse` hook on `WebSearch`** — every Claude-initiated web search is
  denied with a reason that tells the model to call `agy-route search` via the
  Bash tool instead. Deterministic: Claude never needs to remember to prefer
  `agy-route`.
- A slim **`agy-web-search` skill** that documents `agy-route` for Claude —
  useful when the hook is disabled, or when Claude wants to call `agy-route`
  directly for queries that wouldn't trigger `WebSearch`.
- A **`/agy-search "<query>"` slash command** for an explicit one-shot search
  (only registered when you install via the marketplace path; see the callout
  above).
- **Deep-research recipe** (`agy-route research fetch` + `agy-route research
  quote` + `/agy-research <topic>` slash command + `agy-route-research`
  skill): Claude plans + verifies + synthesizes, agy does the cheap
  grounded legwork. Cited report with per-claim verification status.
  See the *Deep research* section below.
- The **`agy-route` Python wrapper** (`src/agy_route/cli.py`, distributed via
  `uv tool install`) that:
  - locks the search down to a `search_web`-only tool policy,
  - auto-selects the latest `gemini-*-flash-high` from `agy models`,
  - classifies failures (`quota` · `auth` · `timeout` · `permission-denied` · …)
    with stable exit codes.

No MCP server required. Skills + commands + a thin Python wrapper + a Claude Code
hook.

## Install

### Recommended: lite install (no marketplace)

Two commands. The plugin's `PreToolUse` hook + the SKILL.md get dropped into
`~/.claude/` directly. No marketplace, no plugin registry, no registry
updates — just files.

```bash
# 1. Install the agy CLI and authenticate:
#    https://antigravity.google/docs/cli-using
agy models                       # should list Gemini Flash / Pro entries

# 2. Install `agy-route` as a uv tool (puts `agy-route` and
#    `agy-route-hook-pretooluse` on $PATH under ~/.local/bin):
uv tool install git+https://github.com/hsuanguo/agy-route

# 3. Drop the SKILL.md and hook into Claude Code:
agy-route install                # SKILL.md + hook for Claude Code (default)
# Optional flags:
#   agy-route install --skill-only   # just the SKILL.md
#   agy-route install --hook-only    # just the hook
#   agy-route install --dry-run      # show what would change, no filesystem writes
#   agy-route install --target <name>  # other targets (currently: claude only)
```

That's it. Verify with:

```bash
agy-route types
agy-route search "latest Antigravity CLI release"
```

The hook is wired automatically. You can confirm by asking Claude a question
that would normally trigger a web search; the response will cite Gemini-grounded
URLs.

### Optional: plugin marketplace path

Use this only if you want the `/agy-search` slash command, versioned
`/plugin update`, or marketplace browsability. Adds a `/plugin marketplace
add` + `/plugin install` step but gives you those features.

```bash
uv tool install git+https://github.com/hsuanguo/agy-route
/plugin marketplace add https://github.com/hsuanguo/agy-route
/plugin install agy-web-search
```

You can switch between paths any time — `agy-route uninstall` reverses the
lite install, `/plugin uninstall agy-web-search` reverses the marketplace one.
The two paths don't conflict; if you install both, the second is a no-op
(idempotent).

## Usage

### From Claude Code

Once the plugin is enabled, **every `WebSearch` is automatically routed through
`agy-route search`** by the hook. To force an explicit search:

```
/agy-search "Claude API pricing June 2026"
```

### From any shell

```bash
# Single-shot search
agy-route search "latest Antigravity CLI release"

# Deep-research primitives
agy-route research fetch "<sub-question>"      # fan-out: 5-8 bullets + URLs + dates
agy-route research quote "<claim>" "<url>"     # URL-quote: verbatim supporting text or NOT SUPPORTED

# Piped prompt (preferred for long queries)
echo "What changed in Python 3.13 between rc1 and final?" | agy-route search

# Programmatic JSON envelope
echo "query" | agy-route search --json
# → {"success":true,"model_used":"...","type":"search","duration_seconds":9,"response":"..."}
```

### Deep research

For multi-source research ("research X", "investigate Y", "find me sources
for Z"), use the `/agy-research <topic>` slash command. It drives the
deep-research recipe:

1. **Plan** (Claude): decompose into 3–6 sub-questions; flag load-bearing claims.
2. **Fan-out fetch** (parallel `agy-route research fetch`): 5–8 bullets per sub-question with URLs + dates.
3. **URL-quote** (parallel `agy-route research quote "<claim>" "<url>"`): agy opens the URL and quotes the verbatim sentence(s) supporting each claim (or `NOT SUPPORTED`).
4. **Verify** (Claude): each load-bearing claim needs ≥2 independent quoted sources → verified or unverified.
5. **Synthesize** (Claude): write the cited report with verified findings + an explicit unverified section.

Steps 1, 4, 5 are Claude reasoning (no CLI). Steps 2, 3 are agy calls.

### Re-install after a `git pull`

```
uv tool install --force --from git+https://github.com/hsuanguo/agy-route agy-route
```

## Exit codes

| code | meaning              | typical action                                  |
|-----:|----------------------|-------------------------------------------------|
|   0  | ok                   |                                                 |
|   2  | failed (args, etc.)  | fix the call                                    |
|   3  | empty output         | inspect stderr; usually quota/auth              |
|  10  | quota                | retry later (or upgrade plan)                   |
|  11  | auth                 | re-auth `agy`                                   |
|  12  | timeout              | pass `--timeout 600`, simplify the query       |
|  13  | agy-missing          | install `agy` and ensure it's on `$PATH`        |
|  14  | model-unavailable    | `rm ~/.cache/agy-route-models` and retry        |
|  15  | permission-denied    | retry with `AGY_SKIP_PERMISSIONS=1`             |

## Environment overrides

| var                        | effect                                                                                  |
|----------------------------|-----------------------------------------------------------------------------------------|
| `AGY_ROUTE_FORCE_MODEL=1`  | pass `--model` to `agy` (off by default; the resolved model is still reported in JSON)   |
| `AGY_SKIP_PERMISSIONS=1`   | pass `--dangerously-skip-permissions` to `agy` (off by default; the policy already gates) |

## Uninstall

```bash
# Reverse the lite install:
agy-route uninstall                # removes SKILL.md + hook for every registered target
agy-route uninstall --target claude  # restrict to one target
uv tool uninstall agy-route

# Reverse the marketplace install (if you used it):
/plugin uninstall agy-web-search
```

The two paths don't conflict — uninstall each one you actually used.

## Layout

```
assets/
  logo.svg                    # horizontal lockup (icon + wordmark)
  icon.svg                    # icon only (favicon / social-card)
tools/
  generate_logo.py            # regenerates assets/*.svg from the letterforms
.claude-plugin/
  plugin.json                 # plugin manifest (skills + commands + hooks)
  marketplace.json            # marketplace entry (for /plugin marketplace add — opt-in)
hooks/
  hooks.json                  # PreToolUse hook wiring (WebSearch → agy-route)
commands/
  agy-search.md               # /agy-search <query> slash command (marketplace path only)
skills/
  agy-web-search/SKILL.md     # intent-surface skill (hook is the tool-call surface)
src/agy_route/
  cli.py                      # Typer app: search / types / targets / install / uninstall
  install.py                  # orchestrator for `agy-route install/uninstall`
  install_data/
    skill.md                  # mirror of skills/agy-web-search/SKILL.md (for lite install)
    hooks.json                # mirror of hooks/hooks.json (for lite install)
  targets/
    base.py                   # Target ABC
    claude.py                 # Claude Code target (~/.claude/ + settings.json)
  hooks/
    pretooluse.py             # the hook binary — `agy-route-hook-pretooluse`
  policies/
    search.md                 # tool policy: search_web + read_url only
pyproject.toml                # PEP 621 metadata + 2 console script entries
```

## Logo

`assets/logo.svg` is a horizontal lockup in the [act-cli](https://github.com/hsuanguo/act-cli/blob/main/assets/logo.svg)
style: an icon (input bar → junction → two branches, the "split-route" idea)
plus a pixel-block wordmark "agy-route". The fill flips black ↔ near-white
via `prefers-color-scheme`. `assets/icon.svg` is the icon-only version
(useful for favicons / social cards).

Both files are derived from `tools/generate_logo.py` — tweak the
`LETTERS` dict in that script and re-run to regenerate.

## Privacy

`agy-route` sends your prompt to Google's Gemini service. Do **not** pipe
credentials, API keys, or PII.

## License

MIT — see [`LICENSE`](./LICENSE).