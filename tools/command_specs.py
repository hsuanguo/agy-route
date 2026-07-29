"""Source of truth for the slash commands shipped by agy-route.

Each `CommandSpec` becomes a `<name>.md` slash command in both Claude Code
(plugin tree → `commands/`) and opencode (`opencode-commands/`). The body
file is loaded from `tools/bodies/<name>.md` — pure markdown with no
frontmatter and no vendor-specific syntax.

Adding a new command:

1. Drop a body markdown file at `tools/bodies/<name>.md`.
2. Add a `CommandSpec(...)` entry to `COMMAND_SPECS` below.
3. Run `python3 tools/generate_commands.py`.

`tools/generate_commands.py` renders both formats with one pass per vendor;
Claude Code ignores the `opencode_*` fields, opencode uses them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Optional


_BODIES_DIR = Path(__file__).resolve().parent / "bodies"


@dataclass
class CommandSpec:
    name: str
    description: str
    argument_hint: Optional[str] = None
    body: str = ""
    # opencode-only optional fields; Claude Code ignores them.
    opencode_agent: Optional[str] = None
    opencode_model: Optional[str] = None
    opencode_subtask: Optional[bool] = None

    @classmethod
    def load(cls, *, name: str, description: str, **kwargs) -> "CommandSpec":
        body_path = _BODIES_DIR / f"{name}.md"
        return cls(
            name=name,
            description=description,
            body=body_path.read_text() if body_path.is_file() else "",
            **kwargs,
        )


COMMAND_SPECS: list[CommandSpec] = [
    CommandSpec.load(
        name="agy-search",
        description=(
            "Run a grounded web search via the agy CLI (Gemini, with citations). "
            "Drop-in for Claude's built-in WebSearch tool."
        ),
        argument_hint="<query>",
    ),
    CommandSpec.load(
        name="agy-research",
        description=(
            "Multi-source deep research via agy-route: plan → fan-out fetch → "
            "URL-quote verification → cited synthesis."
        ),
        argument_hint="<topic>",
        opencode_subtask=True,
    ),
]
