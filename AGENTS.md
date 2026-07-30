# AGENTS.md

This document serves as the guide for AI coding assistants (agents) operating on the `agy-route` repository. It outlines project architecture, design conventions, core workflows, and development guidelines.

---

## Project Overview

`agy-route` is a policy-gated proxy CLI and multi-agent plugin system for Google Antigravity (`agy`). It intercepts and reroutes web search and deep-research requests from AI agent frameworks (such as **Claude Code** and **opencode**) through `agy` (Gemini with grounded Google Search).

### Key Surfaces Today
- **`agy-web-search`**: Single-shot grounded web search via `PreToolUse` hook (Claude Code) or JS plugin (opencode), redirecting `websearch` tool calls to `agy-route search`.
- **`agy-route-research`**: Multi-source deep-research recipe using `agy-route research fetch` (fan-out) and `agy-route research quote` (URL claim verification), exposed via `/agy-research`.

---

## Repository Structure & Architecture

```
agy-route/
├── assets/                          # SVG brand assets (logo, icon)
├── tools/                           # Code & asset generator scripts (Source of Truth)
│   ├── command_specs.py             # Declarative specs for slash commands
│   ├── generate_commands.py         # Generates commands/ & opencode-commands/ from specs (--check supported)
│   ├── generate_logo.py             # Regenerates SVG brand assets from letterforms
│   └── bodies/                      # Markdown command body templates (agy-search, agy-research)
├── commands/                        # Generated Claude Code slash commands
├── opencode-commands/               # Generated opencode slash commands (richer frontmatter)
├── opencode-plugin/                 # JS plugin for opencode (~30 LOC hook handler)
├── hooks/                           # Hook configuration files (Claude Code PreToolUse)
├── skills/                          # Agent skill definitions (SKILL.md)
├── config/                          # Configuration files and policies
│   └── policies/search.md           # Tool policy limiting agy to search_web & read_url
├── src/agy_route/                   # Core Python application package
│   ├── cli.py                       # Main Typer app CLI entry point (search, research, types, etc.)
│   ├── install.py                   # Orchestrator for target installation & uninstallation
│   ├── core/                        # Service logic: models.py, policy.py, executor.py
│   ├── hooks/                       # Executable hook handlers (e.g. pretooluse.py)
│   └── targets/                     # Polymorphic Target ABC abstractions (claude.py, opencode.py)
└── pyproject.toml                   # Hatchling build configuration & console script entrypoints
```

---

## Core Architecture & Guidelines

### 1. Single Source of Truth for Commands & Assets
- **Do NOT edit files in `commands/` or `opencode-commands/` directly.**
- Edit `tools/command_specs.py` and the markdown templates in `tools/bodies/`.
- Run `python3 tools/generate_commands.py` to regenerate both Claude Code and opencode command markdowns simultaneously.
- Verify generation via `python3 tools/generate_commands.py --check`.

### 2. Single Source of Truth for Package Assets (No `install_data` Mirror)
- Root asset directories (`skills/`, `hooks/`, `commands/`, `opencode-plugin/`, `opencode-commands/`, `config/`) ship directly inside the Python wheel via Hatchling's `force-include` in `pyproject.toml`.
- Package code accesses these files dynamically via `importlib.resources.files("agy_route.<package>")`. Do NOT create duplicate copies in Python package subdirectories.

### 3. Target Abstraction Pattern (`Target` ABC)
- All agent target integrations inherit from `Target` in `src/agy_route/targets/base.py`.
- Target subclasses encapsulate their own installation (`install_target`) and uninstallation (`uninstall_target`) logic polymorphically.
- To add support for a new AI coding agent (e.g. Cursor, Aider):
  1. Create a new target class in `src/agy_route/targets/<target_name>.py`.
  2. Implement `install_target()`, `uninstall_target()`, and target availability checks.
  3. Register the target in `src/agy_route/targets/__init__.py`.

### 4. Policy Enforcement & Safety
- `agy-route` passes `--policy` to `agy` using `config/policies/search.md` (shipped in wheel).
- Strictly enforce search-only operations: `search_web` and `read_url` only. No file system mutations, no shell commands, no arbitrary code execution.
- Maintain idempotency and safety in all install/uninstall operations (e.g., auto-backup `~/.claude/settings.json` before modifications).

---

## Development & Verification Workflows

### Environment Setup & Local Installation
```bash
# Install package locally in editable mode or as a uv tool
uv tool install --force .

# Verify CLI commands are accessible
agy-route types
agy-route search "Antigravity CLI"
```

### Command Generation & Asset Maintenance
```bash
# Check if slash commands are up to date
python3 tools/generate_commands.py --check

# Regenerate slash commands for all target frameworks
python3 tools/generate_commands.py

# Regenerate brand logo and icon SVGs
python3 tools/generate_logo.py
```

### Target Testing
```bash
# Test target listing
agy-route targets

# Dry-run target installation without modifying system configuration
agy-route install --target claude --dry-run
agy-route install --target opencode --dry-run

# Verify JS plugin syntax (for opencode target)
node --check opencode-plugin/agy-route.js
```

---

## Exit Code Reference Table

When extending or debugging `agy-route`, use standard exit codes defined in `src/agy_route/core/executor.py`:

| Exit Code | Constant / Meaning | Typical Cause / Resolution |
|:---------:|:-------------------|:---------------------------|
| `0` | Success | Command completed cleanly |
| `2` | Failure / Invalid Args | Incorrect arguments passed to CLI |
| `3` | Empty Output | Output from `agy` was empty (check auth/quota) |
| `10` | Quota Exceeded | Rate limited or quota exhausted |
| `11` | Auth Error | `agy` credentials expired or missing |
| `12` | Timeout | `agy` execution exceeded timeout limit |
| `13` | `agy` Missing | `agy` CLI binary is not installed or on `$PATH` |
| `14` | Model Unavailable | Model resolution failed (`rm ~/.cache/agy-route-models`) |
| `15` | Permission Denied | Policy permission rejected |

---

## Conventions for AI Agents

1. **Clean Code & Typings**: Maintain strict typing in Python (`typing.Optional`, `Path`, etc.) and follow standard PEP 8 formatting.
2. **Preserve User Settings**: Installers must never wipe pre-existing user configurations or hooks. Always namespace tagged entries (`_meta.agy_route = 'agy-route'`).
3. **No Unwanted Output in Scripting**: PreToolUse hooks and programmatic endpoints (`--json`) must produce clean JSON without extraneous standard error or log noise.
4. **Documentation**: Update `CHANGELOG.md` and `README.md` alongside any functional changes or target additions.
