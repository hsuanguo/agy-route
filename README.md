# agy-route — `agy-web-search` plugin

A Claude Code plugin that **routes web searches through the `agy` CLI** (Google
Antigravity CLI — Gemini under the hood). When this plugin is enabled, Claude
uses `agy`'s grounded web search with real source citations instead of its
built-in `WebSearch` / `web_search` tool.

This is the first plugin in the [`agy-route`](.) repo. Future plugins will
delegate review, code, and deep-research tasks the same way.

## What you get

- A `agy-web-search` skill that triggers Claude to use agy for any
  web-search-shaped request ("look up …", "latest …", "search for …", etc.).
- A `/agy-search "<query>"` slash command for an explicit one-shot search.
- The `agy-route` Python wrapper (`src/agy_route/cli.py`, distributed via `uv
  tool install`) that:
  - locks the search down to a `search_web`-only tool policy,
  - auto-selects the latest `gemini-*-flash-high` from `agy models`,
  - classifies failures (`quota` · `auth` · `timeout` · `permission-denied` · …)
    with stable exit codes.

No MCP server required. Skills + commands + a thin Python wrapper only.

## Install

1. **Install `agy` and authenticate.** See
   [Antigravity CLI docs](https://antigravity.google/docs/cli-using). Confirm with
   `agy models` (should list Gemini Flash / Pro entries).
2. **Install `agy-route` as a uv tool.** This puts it on `$PATH` under
   `$HOME/.local/bin`:
   ```
   uv tool install git+https://github.com/hsuanguo/agy-route
   ```
   (Or from a local checkout: `uv tool install /path/to/agy-route`.)
3. **Add the plugin from this repo.** From Claude Code:
   ```
   /plugin marketplace add https://github.com/hsuanguo/agy-route
   /plugin install agy-web-search
   ```
   Or install directly from a local checkout:
   ```
   /plugin install /path/to/agy-route
   ```
4. **Verify.**
   ```
   agy-route types
   agy-route search "latest Antigravity CLI release"
   ```

## Usage

### From Claude Code

Once the plugin is enabled, Claude will route web searches through agy
automatically. To force an explicit search:

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
uv tool uninstall agy-route
/plugin uninstall agy-web-search
```

## Layout

```
.claude-plugin/
  plugin.json                 # plugin manifest (name/version/skills/commands)
  marketplace.json            # marketplace entry (for /plugin marketplace add)
commands/
  agy-search.md               # /agy-search <query> slash command
skills/
  agy-web-search/SKILL.md     # the routing skill
src/agy_route/
  cli.py                      # the Typer app — `agy-route` entry point
  __init__.py
pyproject.toml                # PEP 621 metadata + console script entry
config/
  policies/
    search.md                 # tool policy: search_web + read_url only
```

## Privacy

`agy-route` sends your prompt to Google's Gemini service. Do **not** pipe
credentials, API keys, or PII.

## License

MIT — see [`LICENSE`](./LICENSE).