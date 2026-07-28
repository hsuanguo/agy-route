# Changelog

## 0.2.0 — 2026-07-28

**Added**
- `agy-route install` / `agy-route uninstall` / `agy-route targets`
  subcommands for the **lite install** path. Drops the SKILL.md and
  PreToolUse hook directly into `~/.claude/` (or whatever target the
  user picks via `--target`), no marketplace needed.
  - `--skill-only`, `--hook-only`, `--dry-run` flags.
  - Idempotent — re-running is a no-op when nothing has changed.
  - Auto-backup of `~/.claude/settings.json` to `.bak.<mtime>` before
    any write.
  - Namespace-tagged hook entries (`_meta.agy_route = "agy-route"`)
    so `agy-route uninstall` only touches entries we wrote, never the
    user's other hook config.
  - Scan-all uninstall: `agy-route uninstall` (no `--target`) walks
    every registered target and removes whatever it finds.
  - Target abstraction (`src/agy_route/targets/`) — adding a new
    target is one new file + a registration line. Currently only
    `claude` is registered.
- `src/agy_route/install_data/skill.md` + `hooks.json` — mirrors of the
  plugin tree, packaged in the wheel via `importlib.resources`. No
  repo clone required to run `agy-route install`.
- `skills/agy-web-search/SKILL.md` — restored as the **intent-surface
  layer** alongside the hook (tool-call surface). Broader trigger
  catalog ("with sources", "find a citation", "what does X's docs
  say", "verify against", "as of", etc.) so Claude reaches for
  `agy-route search` directly via Bash for paraphrased search
  requests that wouldn't trigger `WebSearch`.

## 0.1.0 — 2026-07-27

First release of the `agy-web-search` plugin.

**Added**
- `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` manifest.
- `skills/agy-web-search/SKILL.md` — slim reference skill for `agy-route`.
- `commands/agy-search.md` — `/agy-search "<query>"` slash command.
- `hooks/hooks.json` + `src/agy_route/hooks/pretooluse.py` — `PreToolUse`
  hook on `WebSearch` that denies the call and tells Claude to run
  `agy-route search "<query>"` via Bash instead.
- `pyproject.toml` — PEP 621 metadata + `agy-route` + `agy-route-hook-pretooluse`
  console scripts. Installable with `uv tool install git+https://github.com/hsuanguo/agy-route`.
- `src/agy_route/cli.py` — Typer app: `agy-route search "<query>"`,
  `agy-route types`. Search-only tool policy, model auto-resolved from
  `agy models` and cached 60 min at `~/.cache/agy-route-models`. Stable
  exit codes 0/2/3/10/11/12/13/14/15; `--json` envelope.
  Verified end-to-end against `agy 1.1.1`: real `search_web` calls,
  real URLs (Wikipedia, Forbes, UN, e-Stat, Weather Underground, KQED).

**Naming history**
- v0.1.0 went out under `agy-bridge` + bash (`scripts/agy_bridge.sh`).
- Same v0.1.0 line renamed the wrapper to `agy-route` (Typer + Python)
  and renamed the *repo* from `agy-harness` → `agy-route` so
  binary / package / repo are aligned. The bash wrapper is gone; the
  PreToolUse hook drives routing.
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