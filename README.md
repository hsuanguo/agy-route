# agy-route — `agy-web-search` plugin

A Claude Code plugin that **routes web searches through the `agy` CLI** (Google
Antigravity CLI — Gemini under the hood). When this plugin is enabled, Claude's
built-in `WebSearch` tool is intercepted by a `PreToolUse` hook and rerouted to
`agy-route search`, which uses `agy`'s grounded web search with real source
citations.

This is the first plugin in the [`agy-route`](.) repo. Future plugins (review,
research, …) become subcommands of the same `agy-route` binary.

## What you get

- **`PreToolUse` hook on `WebSearch`** — every Claude-initiated web search is
  denied with a reason that tells the model to call `agy-route search` via the
  Bash tool instead. Deterministic: Claude never needs to remember to prefer
  `agy-route`.
- A slim **`agy-web-search` skill** that documents `agy-route` for Claude —
  useful when the hook is disabled, or when Claude wants to call `agy-route`
  directly for queries that wouldn't trigger `WebSearch`.
- A **`/agy-search "<query>"` slash command** for an explicit one-shot search.
- The **`agy-route` Python wrapper** (`src/agy_route/cli.py`, distributed via
  `uv tool install`) that:
  - locks the search down to a `search_web`-only tool policy,
  - auto-selects the latest `gemini-*-flash-high` from `agy models`,
  - classifies failures (`quota` · `auth` · `timeout` · `permission-denied` · …)
    with stable exit codes.

No MCP server required. Skills + commands + a thin Python wrapper + a Claude Code
hook.

## Install

1. **Install `agy` and authenticate.** See
   [Antigravity CLI docs](https://antigravity.google/docs/cli-using). Confirm with
   `agy models` (should list Gemini Flash / Pro entries).
2. **Install `agy-route` as a uv tool.** This puts both `agy-route` and the
   hook binary `agy-route-hook-pretooluse` on `$PATH` under `$HOME/.local/bin`:
   ```
   uv tool install git+https://github.com/hsuanguo/agy-route
   ```
   (Or from a local checkout: `uv tool install /path/to/agy-route`.)
3. **Drop the SKILL.md and hook into Claude Code.** Two equivalent paths:

   **A. Plugin marketplace path** (managed — recommended for most users):
   ```
   /plugin marketplace add https://github.com/hsuanguo/agy-route
   /plugin install agy-web-search
   ```

   **B. `agy-route install` lite path** (no marketplace, drops into `~/.claude/`):
   ```
   agy-route install                # install SKILL.md + hook for Claude Code
   agy-route install --skill-only   # just the SKILL.md
   agy-route install --hook-only    # just the hook
   agy-route install --dry-run      # show what would change, no filesystem writes
   ```
   Targets other than `claude` (default) are opt-in via `--target`. Currently
   registered: `claude`. Run `agy-route targets` for the live list.

4. **Verify.**
   ```
   agy-route types
   agy-route search "latest Antigravity CLI release"
   ```
   The hook is wired automatically. You can confirm by asking Claude a
   question that would normally trigger a web search; the response will cite
   Gemini-grounded URLs.

## Usage

### From Claude Code

Once the plugin is enabled, **every `WebSearch` is automatically routed through
`agy-route search`** by the hook. To force an explicit search:

```
/agy-search "Claude API pricing June 2026"
```

### From any shell

```bash
# Inline
agy-route search "latest Antigravity CLI release"

# Piped prompt (preferred for long queries)
echo "What changed in Python 3.13 between rc1 and final?" | agy-route search

# Programmatic JSON envelope
echo "query" | agy-route search --json
# → {"success":true,"model_used":"...","type":"search","duration_seconds":9,"response":"..."}
```

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

```
agy-route uninstall                # removes SKILL.md + hook for every registered target
agy-route uninstall --target claude  # restrict to one target
uv tool uninstall agy-route
/plugin uninstall agy-web-search    # if you installed via the plugin path
```

## Layout

```
.claude-plugin/
  plugin.json                 # plugin manifest (skills + commands + hooks)
  marketplace.json            # marketplace entry (for /plugin marketplace add)
hooks/
  hooks.json                  # PreToolUse hook wiring (WebSearch → agy-route)
commands/
  agy-search.md               # /agy-search <query> slash command
skills/
  agy-web-search/SKILL.md     # reference skill (the hook does the routing)
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

## Privacy

`agy-route` sends your prompt to Google's Gemini service. Do **not** pipe
credentials, API keys, or PII.

## License

MIT — see [`LICENSE`](./LICENSE).