# Changelog

## 0.1.0 — 2026-07-27

First release of the `agy-web-search` plugin.

**Added**
- `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` manifest.
- `skills/agy-web-search/SKILL.md` — Claude uses agy for any
  web-search-shaped request when the skill is active.
- `commands/agy-search.md` — `/agy-search "<query>"` slash command for
  explicit one-shot searches.
- `pyproject.toml` — PEP 621 metadata; declares `agy-route` as a console
  script entry point. Installable with `uv tool install
  git+https://github.com/hsuanguo/agy-route`.
- `src/agy_route/cli.py` — Typer app, the `agy-route` wrapper:
  - `agy-route search "<query>"` (v0.1.0; `--type search` only).
  - Tool policy inlined as part of the prompt (search-web only).
  - Model auto-resolved from `agy models`, cached 60 min
    at `~/.cache/agy-route-models`; reported in the JSON envelope.
    `AGY_ROUTE_FORCE_MODEL=1` opts into passing `--model` to `agy`.
  - Stable exit codes: 0 · 2 · 3 · 10 (quota) · 11 (auth) · 12 (timeout) ·
    13 (agy-missing) · 14 (model-unavailable) · 15 (permission-denied).
  - `--json` envelope: `success`, `type`, `model_used`, `duration_seconds`,
    `response` / `error_class` / `error`.
  - Verified end-to-end against `agy 1.1.1`: real `search_web` calls,
    real URLs in the response (Tokyo population, SF weather, Paris,
    Anthropic CEO).

**Naming history**
- v0.1.0 went out under `agy-bridge` + bash (`scripts/agy_bridge.sh`).
- Renamed to `agy-route` (Typer + Python) in the same v0.1.0 line —
  the upstream commit replacing the bash wrapper has not been tagged
  with a new version; the source-of-truth is `main`.
- `scripts/install.sh` — pinned wrapper installer; idempotent; backs up
  any pre-existing shim at `~/.local/bin/agy-bridge`.
- `scripts/uninstall.sh` — reverses the install; refuses to delete files
  not written by this plugin.
- `config/policies/search.md` — search-only tool policy
  (`search_web`, `read_url`, `read_url_content`; everything else forbidden).
- README with install + usage + exit-code table; MIT LICENSE.

**Limitations**
- Only `--type search` is implemented. Review / code / analysis /
  implement are scaffolded in the bridge's args parser but rejected
  (`exit 2`) — they land in a later release.
- No `setup` / `uninstall` slash commands yet — the README points at the
  raw `scripts/install.sh` / `scripts/uninstall.sh` for now.
- No hooks (`hooks/hooks.json`) yet — the search routing is opt-in
  via the skill and the explicit `/agy-search` command.