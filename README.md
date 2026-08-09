# Antigravity Route

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo.svg">
    <img alt="agy-route" src="assets/logo.svg" width="480">
  </picture>
</p>

A Claude Code **and** opencode plugin (and CLI) that routes work through the **`agy` CLI** (Google Antigravity CLI — Gemini under the hood). Ships two surfaces today:

- **`agy-web-search`** — single-shot grounded web search. A `PreToolUse` hook (Claude Code) or JS plugin (opencode) intercepts the agent's `websearch` tool calls and reroutes them to `agy-route search`, which uses agy's `search_web` with real source citations.
- **`agy-research`** — multi-source deep research. Claude plans, fans out sub-questions via `agy-route research fetch`, verifies each load-bearing claim by URL-quote via `agy-route research quote`, then synthesizes a cited report. Run with `/agy-research <topic>`.

Both surfaces use the same `agy-route` binary (`uv tool install`), the same search-only tool policy (no file writes, no shell — `search_web` + `read_url` only), and the same exit-code conventions. `agy-route install` is target-aware: it drops skills + hooks + commands into whichever agent you pick (`claude` or `opencode`).

This is the first plugin in the [`agy-route`](.) repo. Future plugins (review, code, …) become subcommands of the same `agy-route` binary.

## Install

Choose one of two installation methods depending on your workflow:

### Option 1: Direct CLI Install (Recommended)

Quick, lightweight setup. Drops skills, slash commands, and hooks directly into your target agent's configuration directory (`~/.claude/` or `~/.config/opencode/`). No marketplace registry needed.

```bash
# 1. Install the agy CLI and authenticate (https://antigravity.google/docs/cli-using):
agy models                       # should list Gemini Flash / Pro entries

# 2. Install `agy-route` as a uv tool:
uv tool install git+https://github.com/hsuanguo/agy-route

# 3. Drop skills and slash commands into target agent:
agy-route install --target claude        # target agent: claude (default) or opencode

# Optional flags:
#   agy-route install --with-hook        # also install PreToolUse hook (Claude) / JS plugin (opencode)
#   agy-route install --only-skill       # install SKILL.md files only
#   agy-route install --only-hook        # install hook / JS plugin only
#   agy-route install --dry-run          # preview changes without writing files
```

### Option 2: Claude Code Marketplace Install

Use this path if you prefer managing plugins via Claude Code's native `/plugin` system (provides versioned `/plugin update` and `/plugin marketplace browse`).

```bash
# 1. Install `agy-route` as a uv tool:
uv tool install git+https://github.com/hsuanguo/agy-route

# 2. Add the marketplace registry inside Claude Code:
/plugin marketplace add https://github.com/hsuanguo/agy-route

# 3. Install skills and slash commands (/agy-web-search, /agy-research):
/plugin install agy-route

# Optional: Also install the PreToolUse hook to automatically intercept standard WebSearch tool calls:
/plugin install agy-route-hook
```

> **Note:** You can switch between installation paths at any time — `agy-route uninstall` reverses Option 1, and `/plugin uninstall agy-route` (or `/plugin uninstall agy-route-hook`) reverses Option 2. The two paths do not conflict and are idempotent.

### Verification

Verify with:

```bash
agy-route types
agy-route search "latest Antigravity CLI release"
```

The hook is wired automatically. You can confirm by asking Claude a question that would normally trigger a web search; the response will cite Gemini-grounded URLs.

## Usage

### From Claude Code

Once the plugin is enabled, **every `WebSearch` is automatically routed through `agy-route search`** by the hook. To force an explicit search:

```
/agy-web-search "Claude API pricing June 2026"
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
agy-route uninstall                # removes SKILL.md + hook/plugin for every registered target
agy-route uninstall --target claude    # restrict to one target
agy-route uninstall --target opencode  # restrict to one target
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
.claude-plugin/
  plugin.json                 # plugin manifest (skills + hooks)
  marketplace.json            # marketplace entry (for /plugin marketplace add — opt-in)
skills/
  agy-web-search/SKILL.md     # single-shot web search skill
  agy-research/SKILL.md       # deep-research skill
plugins/
  claude/hooks.json           # Claude Code PreToolUse hook configuration
  opencode/agy-route.js       # opencode JS plugin
src/agy_route/
  cli.py                      # Typer CLI app entry point
  install.py                  # orchestrator for target installation & uninstallation
  targets/
    base.py                   # Target ABC
    claude.py                 # Claude Code target (~/.claude/ + settings.json)
    opencode.py               # opencode target (~/.config/opencode/{plugins,commands}/)
  hooks/
    pretooluse.py             # the Claude hook binary — `agy-route-hook-pretooluse`
  policies/
    search.md                 # tool policy: search_web + read_url only
pyproject.toml                # PEP 621 metadata + 2 console script entries
```

## Privacy

`agy-route` sends your prompt to Google's Gemini service. Do **not** pipe credentials, API keys, or PII.

## License

MIT — see [`LICENSE`](./LICENSE).