# agy-harness — `agy-web-search` plugin

A Claude Code plugin that **routes web searches through the `agy` CLI** (Google
Antigravity CLI — Gemini under the hood). When this plugin is enabled, Claude
uses `agy`'s grounded web search with real source citations instead of its
built-in `WebSearch` / `web_search` tool.

This is the first plugin in the [`agy-harness`](.) repo. Future plugins will
delegate review, code, and deep-research tasks the same way.

## What you get

- A `agy-web-search` skill that triggers Claude to use agy for any
  web-search-shaped request ("look up …", "latest …", "search for …", etc.).
- A `/agy-search "<query>"` slash command for an explicit one-shot search.
- A hardened shell wrapper, `agy-bridge`, that:
  - locks the search down to a `search_web`-only tool policy,
  - delivers the prompt via a per-run `0600` file (off `argv`/`ps`, off `ARG_MAX`),
  - auto-selects the latest `gemini-*-flash-high` from `agy models`,
  - classifies failures (`quota` · `auth` · `timeout` · `permission-denied` · …)
    with stable exit codes.

No MCP server required. Skills + commands + a thin wrapper only.

## Install

1. **Install `agy` and authenticate.** See
   [Antigravity CLI docs](https://antigravity.google/docs/cli-using). Confirm with
   `agy models` (should list Gemini Flash / Pro entries).
2. **Add the plugin from this repo.** From Claude Code:
   ```
   /plugin marketplace add https://github.com/hsuanguo/agy-harness
   /plugin install agy-web-search
   ```
   Or install directly from a local checkout:
   ```
   /plugin install /path/to/agy-harness
   ```
3. **Pin the `agy-bridge` wrapper.** Inside Claude Code, run:
   ```
   /agy-setup
   ```
   (This is a one-time install; safe to re-run after plugin updates.)
   It writes `~/.local/bin/agy-bridge` to exec this repo's
   `scripts/agy_bridge.sh` (pinned absolute path).
4. **Verify.**
   ```
   agy-bridge --types
   agy-bridge --type search -- "latest Antigravity CLI release"
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
agy-bridge --type search -- "latest Antigravity CLI release"

# Piped prompt (preferred for long queries)
echo "What changed in Python 3.13 between rc1 and final?" | agy-bridge --type search

# Programmatic JSON envelope
echo "query" | agy-bridge --type search --json
# → {"success":true,"model_used":"...","type":"search","duration_seconds":9,"response":"..."}
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
|  13  | agy-missing          | install `agy` and ensure `~/.local/bin` on PATH |
|  14  | model-unavailable    | `rm ~/.cache/agy-bridge-models` and retry       |
|  15  | permission-denied    | retry with `AGY_SKIP_PERMISSIONS=1`             |

## Environment overrides

| var                        | effect                                                                                  |
|----------------------------|-----------------------------------------------------------------------------------------|
| `AGY_BRIDGE_FORCE_MODEL=1` | pass `--model` to `agy` (off by default; the resolved model is still reported in JSON)   |
| `AGY_BRIDGE_DOTEMD=1`      | write the prompt to a 0600 temp file instead of inlining on the command line             |
| `AGY_SKIP_PERMISSIONS=1`   | pass `--dangerously-skip-permissions` to `agy` (off by default; the policy already gates) |

## Uninstall

```
/plugin uninstall agy-web-search
~/.local/bin/agy-uninstall    # or run this repo's scripts/uninstall.sh
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
scripts/
  agy_bridge.sh               # the bridge wrapper (executed by ~/.local/bin/agy-bridge)
  install.sh                  # writes the pinned shim into ~/.local/bin
  uninstall.sh                # reverses the install (refuses to delete other files)
config/
  policies/
    search.md                 # tool policy: search_web + read_url only
```

## Privacy

`agy-bridge` writes your prompt into a per-run `0600` file, but the prompt is
still sent to Google's Gemini service. Do **not** pipe credentials, API keys,
or PII.

## License

MIT — see [`LICENSE`](./LICENSE).