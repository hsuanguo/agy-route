# Changelog

## 0.4.0 — 2026-07-29

**Added**

- **opencode target** (`agy-route install --target opencode`). Skills,
  hooks, and slash commands drop into opencode's standard config dirs;
  opencode auto-loads everything from `~/.config/opencode/{skills,plugins,commands}/`.
  - **Skills** drop into `~/.claude/skills/agy-{web-search,route-research}/SKILL.md`
    — opencode already reads this directory (see opencode `packages/opencode/src/skill/index.ts:21-25`),
    so the existing skill install covers both agents without duplication.
  - **Hook plugin** (`opencode-plugin/agy-route.js`, ~30 LOC) drops into
    `~/.config/opencode/plugins/`. Implements `tool.execute.before` on the
    `websearch` tool; throws the same denial message as the Python
    `agy-route-hook-pretooluse`, so Claude's recovery behavior is
    identical between Claude Code and opencode.
  - **Slash commands** generated from `tools/bodies/<name>.md` →
    `~/.config/opencode/commands/agy-{search,research}.md`.
- **`tools/command_specs.py` + `tools/generate_commands.py`** — single
  source of truth per command (description, body, opencode-only fields),
  rendered to both Claude Code (`commands/<name>.md`) and opencode
  (`opencode-commands/<name>.md`) outputs. Adding a third agent
  framework = add one new renderer; no per-command duplication.
- **Target registry** (`src/agy_route/targets/opencode.py`) — implements
  the existing Target ABC for opencode. Opencode target's
  `install_skill` shares the Claude target's install dir
  (`~/.claude/skills/`); opencode target's `install_plugin` +
  `install_commands` are opencode-specific; `uninstall_hook` removes
  the opencode plugin file + all `agy-*.md` commands.
- **Install data** (`src/agy_route/install_data/`) extended with
  `opencode-plugin/agy-route.js`, `opencode-commands/agy-search.md`,
  `opencode-commands/agy-research.md`. All three shipped inside the
  wheel via `pyproject.toml` `force-include`.
- **`commands/*.md`** regenerated; each file carries a
  `# auto-generated` header comment.
- **`opencode-commands/*.md`** new generated outputs.

**Notes**

- Skill installs for both targets share `~/.claude/skills/` — one
  install covers both agents.
- No `opencode.jsonc` JSON-merge needed: opencode auto-loads `.js`
  files from the plugins dir and `.md` files from the commands dir
  on startup.
- The opencode plugin JS uses the same denial semantics as the Python
  Claude hook: `throw new Error(...)` from `tool.execute.before`
  causes opencode to surface the message as the tool-call error,
  which the model reads and recovers from.

## 0.5.0 — 2026-08-06

**Added**
- **Claude Code `permissions.allow` whitelist** in `~/.claude/settings.json`.
  `agy-route install --target claude` now also merges a `permissions` block
  with `Bash(agy-route search *)` and `Bash(agy-route research *)`,
  auto-allowing every agy-route subcommand without a permission prompt.
  Uninstall strips any `Bash(agy-route ...)` entries we wrote. Idempotent:
  re-running is a no-op.
- **Renamed** `plugins/claude/hooks.json` → `plugins/claude/claude-settings.json`.
  Now the single source of truth for everything we merge into the user's
  `~/.claude/settings.json`: both the `permissions.allow` block (v0.5.0)
  and the `hooks.PreToolUse` block (existing). The `install_data/` mirror
  ships in the wheel via `force-include` on the `plugins/` directory.

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